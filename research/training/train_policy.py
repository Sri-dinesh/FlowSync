#!/usr/bin/env python3
"""Train D3QN on the audited sensor boundary; select ONLY on validation scenarios.

No test scenario is loaded by this program. Every candidate and baseline is
retained; selection is frozen mean validation delay, not a best test seed.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch

from research.experiments.engine import ExperimentRunner
from research.experiments.runtime import ObservedState, apply_scenario_step, build_environment, RESEARCH_REWARD_VERSION
from research.noise.fault_injector import FaultProfile, PerceptionFaultInjector
from research.scenarios.scenario_schema import ScenarioConfig
from research.training.temporal_initialization import initialize_parent
from server.app.controllers import get_controller
from server.app.controllers.safety_shield import SafetyShield
from server.app.rl.dqn_agent import DQNAgent
from server.app.rl.hyperparams import HyperParams
from server.app.rl.observations import (
    OBSERVATION_DIMS, TEMPORAL_VERSIONS, TEMPORAL_SCHEMA, SPATIAL_VERSIONS, SPATIAL_SCHEMA,
    encode_policy_observation,
)

HP = HyperParams()
VALIDATION_SEEDS = (21001, 21002)
VALIDATION_FAULTS = (FaultProfile(), FaultProfile(name="validation_mixed", miss_rate=.2,
                                               latency_ms=200, false_positive_lambda=.1))


class BudgetExceeded(RuntimeError):
    """Stop gracefully without treating partial validation as a valid score."""


class RunBudget:
    """Cooperative deadline; a validation simulation/optimizer step is atomic."""

    def __init__(self, seconds, clock=None):
        if not np.isfinite(seconds) or seconds < 0:
            raise ValueError("Runtime limit must be finite and nonnegative")
        self.clock = clock or time.monotonic
        self.started = self.clock()
        self.seconds = seconds

    @property
    def elapsed(self):
        return self.clock() - self.started

    def check(self, stage):
        if self.seconds and self.elapsed >= self.seconds:
            raise BudgetExceeded(stage)


def load_split(split):
    if split not in ("train", "validation"):
        raise ValueError("Training/selection may not access the final test split")
    scenarios = [ScenarioConfig.load(p) for p in sorted((ROOT / "research/scenarios" / split).glob("*.yaml"))]
    if not scenarios or any(s.split != split for s in scenarios):
        raise ValueError(f"Missing or mislabeled {split} scenarios")
    return scenarios


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def demonstration_weight(initial, final, decay_episodes, episode):
    """Optional online-only release of the teacher margin; TD replay is retained."""
    if not np.isfinite(initial) or initial < 0 or decay_episodes < 0 or episode < 0:
        raise ValueError("Invalid demonstration schedule")
    if final is None:
        if decay_episodes:
            raise ValueError("A decay requires an explicit final demonstration weight")
        return initial
    if not np.isfinite(final) or final < 0 or decay_episodes <= 0:
        raise ValueError("Final weight requires positive decay episodes")
    fraction = min(1., episode / decay_episodes)
    return initial + fraction * (final - initial)


def preserve_rng(function):
    """Evaluation seeds must not change subsequent replay/exploration sampling."""
    py, np_state, ts = random.getstate(), np.random.get_state(), torch.get_rng_state()
    try:
        return function()
    finally:
        random.setstate(py)
        np.random.set_state(np_state)
        torch.set_rng_state(ts)


def training_fault(rng, robust):
    if not robust or rng.random() < .5:
        return FaultProfile()
    return FaultProfile(name="train_randomized", miss_rate=float(rng.uniform(.05, .25)),
                        latency_ms=int(rng.choice([0, 100, 200])),
                        false_positive_lambda=float(rng.uniform(0, .15)))


def training_scenario(template, rng, episode_steps=0, randomize=False):
    """Expand training support without reading validation/test configurations."""
    if template.split != "train":
        raise ValueError("Domain randomization requires a training template")
    data = template.to_dict()
    data["scenario_hash"] = ""
    if episode_steps:
        ratio = episode_steps / template.duration_steps
        data["duration_steps"] = episode_steps
        for events in (data["demand_profile"]["burst_events"], data["demand_profile"]["incident_events"]):
            for event in events:
                event["start_step"] = round(event["start_step"] * ratio)
                event["end_step"] = round(event["end_step"] * ratio)
    if randomize:
        demand = data["demand_profile"]
        demand["base_lambda"] = float(np.clip(demand["base_lambda"] * rng.uniform(.6, 1.6), .2, 1.2))
        for direction in demand["directional_weights"]:
            demand["directional_weights"][direction] = float(np.clip(
                demand["directional_weights"][direction] * rng.lognormal(0, .6), .25, 3))
            turns = rng.dirichlet([4., 2., 1.5])
            demand["turn_ratios"][direction] = dict(zip(("straight", "left", "right"), turns.tolist()))
        if rng.random() < .1:
            duration = data["duration_steps"]
            demand["incident_events"].append({"start_step": int(duration*.35), "end_step": int(duration*.65),
                                               "direction": str(rng.choice(list(demand["directional_weights"]))),
                                               "capacity_factor": float(rng.uniform(.3, .8))})
    return ScenarioConfig.from_dict(data)


def collect_episode(agent, scenario, seed, fault, epsilon, teacher=None, learn=True,
                    target_update=HP.TARGET_UPDATE_FREQ, budget=None, train_with_shield=False):
    """Causal semi-MDP replay using the SAME microtick inputs/FSM as evaluation.

    Truth is used only for the training reward, never for input/masks/teacher.
    Complete decisions bootstrap (the task is continuing). A time limit cutting
    a macro-action short is not a new decision state: discard that partial
    replay item instead of bootstrapping an untrained/locked-state Q value.
    With the optional shield, replay stores the policy's proposed action: the
    shield is part of the transition dynamics, just as during wrapped inference.
    """
    if scenario.split != "train":
        raise ValueError("Replay collection is restricted to training scenarios")
    if budget is not None:
        budget.check("demonstrations" if teacher is not None else "training")
    env, profile = build_environment(scenario)
    obs, _ = env.reset(seed=seed)
    sensor = ObservedState(spatial=agent.obs_version in SPATIAL_VERSIONS)
    injector = PerceptionFaultInjector(fault, seed=seed + 90000)
    shield = SafetyShield() if train_with_shield else None
    if teacher is not None:
        teacher.reset(seed=seed)
    pending = None
    held_action = 0
    decisions, losses = 0, []
    dropped_partial_transition_ticks = 0
    reward_sum = 0.0
    decision_ticks = round(HP.DECISION_DT / .1)

    def finish_transition(next_obs, next_mask):
        nonlocal decisions
        state, mask, action, value, ticks = pending
        agent.replay_buffer.push(state, action, value, next_obs, False,
                                 valid_action_mask=mask, next_valid_action_mask=next_mask,
                                 bootstrap_discount=HP.GAMMA ** (ticks / decision_ticks),
                                 is_demo=teacher is not None)
        decisions += 1
        if learn and len(agent.replay_buffer) >= HP.BATCH_SIZE:
            loss, _ = agent.train_step(agent.replay_buffer.sample(HP.BATCH_SIZE))
            losses.append(loss)
            if agent.step_count % target_update == 0:
                agent.sync_target_network()

    for step in range(scenario.duration_steps + 1):
        if budget is not None:
            budget.check("demonstrations" if teacher is not None else "training")
        if step < scenario.duration_steps:
            apply_scenario_step(env.intersection, profile, scenario.demand_profile, step)
        policy_obs, ctx = sensor.build(env, obs, step, injector)
        network_obs = encode_policy_observation(policy_obs, ctx, agent.obs_version)
        end = step == scenario.duration_steps
        gate = ctx.is_decision_step and (pending is None or pending[4] >= decision_ticks)
        if pending is not None and gate:
            finish_transition(network_obs, ctx.valid_action_mask)
            pending = None
        if end:
            if pending is not None:
                dropped_partial_transition_ticks = pending[4]
            break
        if gate:
            held_action = (teacher.act(policy_obs, ctx) if teacher is not None else
                           agent.select_action(network_obs, epsilon, ctx.valid_action_mask))
            pending = [network_obs.copy(), ctx.valid_action_mask.copy(), held_action, 0.0, 0]
        # Match D3QNController: current phase while transition/min-green is locked.
        action = held_action if ctx.is_decision_step else ctx.current_phase
        if shield is not None:
            action = shield.filter_context(action, ctx).executed_action
        obs, reward, _, _, _ = env.step(action)
        reward_sum += reward
        if pending is not None:
            pending[3] += HP.GAMMA ** (pending[4] / decision_ticks) * reward
            pending[4] += 1
    return {"scenario": scenario.scenario_id, "seed": seed, "fault": asdict(fault),
            "executed_scenario": scenario.to_dict(),
            "shield_enabled": train_with_shield,
            "shield_audit": shield.get_audit_metrics() if shield is not None else None,
            "dropped_partial_transition_ticks": dropped_partial_transition_ticks,
            "reward_components": dict(env.reward_component_accumulators),
            "decisions": decisions, "reward": reward_sum,
            "avg_delay": env.intersection.get_avg_wait_time(),
            "loss": float(np.mean(losses)) if losses else None}


def validation(checkpoint, output, label, include_baselines=False, seeds=VALIDATION_SEEDS,
               budget=None, train_with_shield=False):
    rows = []

    def check_budget():
        if budget is None:
            return
        try:
            budget.check(f"validation_{label}")
        except BudgetExceeded:
            (output / f"validation_{label}.json").write_text(json.dumps({
                "selection_metric": "mean_validation_delay", "score": None,
                "complete": False, "stop_reason": "wall_clock_budget", "rows": rows,
            }, indent=2))
            raise

    check_budget()
    runner = ExperimentRunner()
    version = torch.load(checkpoint, map_location="cpu", weights_only=True).get("obs_version")
    spatial = version in SPATIAL_VERSIONS
    policy_label = "d3qn_shield" if train_with_shield else "d3qn"
    controllers = [policy_label] + (["fixed", "actuated", "greedy", "max_pressure"] if include_baselines else [])
    if spatial and include_baselines:
        controllers.append("max_pressure_upstream")
        if train_with_shield:
            controllers.extend(("max_pressure_shield", "max_pressure_upstream_shield"))
    for scenario in load_split("validation"):
        for seed in seeds:
            for fault in VALIDATION_FAULTS:
                for name in controllers:
                    check_budget()
                    if name == "d3qn_shield":
                        ctrl = get_controller("flowsync_uq", checkpoint_path=str(checkpoint),
                                              enable_shield=True, enable_fallback=False)
                    elif name in ("max_pressure_upstream", "max_pressure_shield", "max_pressure_upstream_shield"):
                        from research.policies.spatial_baselines import UpstreamMaxPressureController
                        from research.experiments.shielded_controller import ShieldedController
                        ctrl = (get_controller("max_pressure") if name == "max_pressure_shield"
                                else UpstreamMaxPressureController())
                        if name.endswith("_shield"):
                            ctrl = ShieldedController(ctrl)
                    else:
                        ctrl = get_controller(name, **({"checkpoint_path": str(checkpoint)} if name == "d3qn" else {}))
                    result = runner.run(ctrl, scenario, seed, record_trajectory=False,
                                        fault_injector=PerceptionFaultInjector(fault, seed=seed + 90000),
                                        spatial_observation=spatial)
                    rows.append({"scenario": scenario.scenario_id, "seed": seed, "fault": fault.name,
                                 "controller": name, "delay": result.avg_delay, "p95": result.p95_delay,
                                 "throughput": result.total_vehicles_passed,
                                 "conflicts": result.executed_conflict_violations,
                                 "clearance_violations": result.executed_clearance_violations,
                                 "safety_samples": result.safety_samples,
                                 "expected_safety_samples": result.num_steps,
                                 "starvations": result.starvation_count,
                                 "checkpoint_hash": result.checkpoint_hash,
                                 "arrivals_hash": result.arrival_trace_hash})
                    check_budget()
    score = float(np.mean([r["delay"] for r in rows if r["controller"] == policy_label]))
    payload = {"selection_metric": "mean_validation_delay", "selection_controller": policy_label,
               "score": score, "complete": True, "rows": rows}
    (output / f"validation_{label}.json").write_text(json.dumps(payload, indent=2))
    return score


def fixed_episode_updates(agent, count, target_update, budget):
    """Complete exactly count optimizer steps, or stop without a completed episode."""
    if len(agent.replay_buffer) < HP.BATCH_SIZE:
        raise ValueError("Insufficient replay for the fixed update budget; collect more demonstrations")
    losses = []
    for _ in range(count):
        budget.check("online_updates")
        loss, _ = agent.train_step(agent.replay_buffer.sample(HP.BATCH_SIZE))
        if not np.isfinite(loss):
            raise ValueError("Non-finite online training loss")
        losses.append(loss)
        if agent.step_count % target_update == 0:
            agent.sync_target_network()
    return float(np.mean(losses))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, help="Optional parent; omit for independent fresh training")
    parser.add_argument("--expand-v7-parent", action="store_true",
                        help="Explicitly zero-expand a v7 parent into a matched v8/v9 research network")
    parser.add_argument("--updates-per-episode", type=int,
                        help="Opt-in fixed optimizer budget after each complete episode; defaults to per-transition updates")
    parser.add_argument("--episodes", type=int, default=120)
    parser.add_argument("--seed", type=int, default=101)
    parser.add_argument("--validate-every", type=int, default=30)
    parser.add_argument("--demo-episodes", type=int, default=24)
    parser.add_argument("--pretrain-updates", type=int, default=300)
    parser.add_argument("--learning-rate", type=float, default=1e-4)
    parser.add_argument("--clean-only", action="store_true")
    parser.add_argument("--observation-version", choices=tuple(OBSERVATION_DIMS), default=HP.OBS_VERSION)
    parser.add_argument("--imitation-updates", type=int, default=0,
                        help="Optional masked cross-entropy warm start on observed Max-Pressure demonstrations")
    parser.add_argument("--target-update", type=int, default=HP.TARGET_UPDATE_FREQ)
    parser.add_argument("--domain-randomization", action="store_true")
    parser.add_argument("--train-with-shield", action="store_true",
                        help="Apply the inference shield during replay and validation; fallback remains disabled")
    parser.add_argument("--episode-steps", type=int, default=0, help="0 preserves template duration")
    parser.add_argument("--validation-seeds", type=int, nargs="+", default=list(VALIDATION_SEEDS))
    parser.add_argument("--skip-initial-baselines", action="store_true",
                        help="Policy-only development comparison; skip redundant fixed/classical initial runs, not policy validation")
    parser.add_argument("--demo-loss-weight", type=float, default=.1)
    parser.add_argument("--demo-loss-final-weight", type=float,
                        help="Optional final online imitation-margin weight; TD learning still uses demonstrations")
    parser.add_argument("--demo-loss-decay-episodes", type=int, default=0,
                        help="Linearly reach the final margin weight after this many online episodes; warmup unchanged")
    parser.add_argument("--max-wall-seconds", type=float, default=0,
                        help="Cooperative limit including warmup/validation; may overrun by one validation run or optimizer step plus saving. 0 disables")
    args = parser.parse_args()
    if args.expand_v7_parent and (not args.checkpoint or args.observation_version not in (*TEMPORAL_VERSIONS, *SPATIAL_VERSIONS)):
        parser.error("--expand-v7-parent requires --checkpoint and a v8/v9 observation version")
    if args.updates_per_episode is not None and args.updates_per_episode < 1:
        parser.error("--updates-per-episode must be positive")
    if min(args.episodes, args.validate_every, args.target_update) < 1 or min(args.demo_episodes, args.pretrain_updates, args.imitation_updates) < 0:
        parser.error("Episodes/validation interval must be positive; warmup cannot be negative")
    if args.episode_steps < 0 or not np.isfinite(args.max_wall_seconds) or args.max_wall_seconds < 0 or not np.isfinite(args.demo_loss_weight) or args.demo_loss_weight < 0 or not np.isfinite(args.learning_rate) or args.learning_rate <= 0:
        parser.error("Invalid duration, loss weight or learning rate")
    if len(set(args.validation_seeds)) != len(args.validation_seeds):
        parser.error("Validation seeds must be unique")
    try:
        demonstration_weight(args.demo_loss_weight, args.demo_loss_final_weight, args.demo_loss_decay_episodes, 0)
    except ValueError as exc:
        parser.error(str(exc))
    budget = RunBudget(args.max_wall_seconds)
    args.output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    scenarios = load_split("train")
    agent = DQNAgent(OBSERVATION_DIMS[args.observation_version], args.observation_version)
    agent.reward_version = RESEARCH_REWARD_VERSION
    if args.checkpoint:
        state = torch.load(args.checkpoint, map_location="cpu", weights_only=True)
        initialize_parent(agent, state, args.expand_v7_parent)
    agent.prepare_for_finetuning(args.learning_rate)
    agent.demonstration_loss_weight = args.demo_loss_weight
    manifest = {"version": "audited_training_v4", "arguments": {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()},
                "hyperparameters": {**asdict(HP), "STATE_DIM": agent.state_dim, "OBS_VERSION": agent.obs_version,
                                    "LEARNING_RATE": args.learning_rate, "TARGET_UPDATE_FREQ": args.target_update},
                "parent_sha256": file_hash(args.checkpoint) if args.checkpoint else None,
                "parent_initialization": (("zero_expand_v7_to_v9" if args.observation_version in SPATIAL_VERSIONS else "zero_expand_v7_to_v8")
                                          if args.expand_v7_parent else "same_version"),
                "observation_schema": (SPATIAL_SCHEMA if args.observation_version in SPATIAL_VERSIONS else
                                       TEMPORAL_SCHEMA if args.observation_version in TEMPORAL_VERSIONS else None),
                "online_update_schedule": ("fixed_after_complete_episode" if args.updates_per_episode else "per_complete_transition"),
                "demonstration_schedule": {"initial": args.demo_loss_weight,
                    "final": args.demo_loss_final_weight, "online_decay_episodes": args.demo_loss_decay_episodes,
                    "replay_preserved": True, "warmup_weight_unchanged": True},
                "training_scenarios": {s.scenario_id: s.compute_hash() for s in scenarios},
                "validation_scenarios": {s.scenario_id: s.compute_hash() for s in load_split("validation")},
                "validation_seeds": args.validation_seeds, "validation_faults": [asdict(f) for f in VALIDATION_FAULTS],
                "selection_rule": "minimum mean validation delay; incumbent retained on ties",
                "selection_controller": "d3qn_shield" if args.train_with_shield else "d3qn",
                "shield_enabled": args.train_with_shield, "fallback_enabled": False,
                "replay_action_semantics": "proposed policy action; shield is part of transition dynamics",
                "reward_version": RESEARCH_REWARD_VERSION,
                "time_limit_replay": "drop incomplete macro-actions; bootstrap only complete decision-to-decision transitions",
                "test_access": False, "watchdogs": False, "teacher": "max_pressure at policy decision gates",
                "source_hashes": {str(p.relative_to(ROOT)): file_hash(p)
                                  for base in (ROOT / "research", ROOT / "server/app") for p in sorted(base.rglob("*.py"))}}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    run_training(args, agent, rng, scenarios, manifest, budget)


def run_training(args, agent, rng, scenarios, manifest, budget):
    """Keep completed selections and explicitly report any interrupted stage."""

    def save(episode, label):
        cp = agent.get_checkpoint_state()
        cp.update(episode=episode, training_seed=args.seed, research_training=manifest,
                  demonstration_loss_weight=agent.demonstration_loss_weight,
                  parent_checkpoint_sha256=manifest["parent_sha256"])
        path = args.output / f"checkpoint_{label}.pt"
        torch.save(cp, path)
        return path

    best = None
    episodes_completed = 0
    counts = {"demonstrations_completed": 0, "imitation_updates_completed": 0,
              "pretrain_updates_completed": 0}
    stop_reason, interrupted_stage, interrupted_checkpoint = "completed", None, None

    def evaluate(candidate, label, episode, include_baselines=False):
        nonlocal best
        score = preserve_rng(lambda: validation(candidate, args.output, label,
                              include_baselines=include_baselines, seeds=args.validation_seeds,
                              budget=budget, train_with_shield=args.train_with_shield))
        if best is None or score < best["score"]:
            best = {"path": str(candidate.resolve()), "score": score, "episode": episode,
                    "evaluation_controller": "d3qn_shield" if args.train_with_shield else "d3qn",
                    "sha256": file_hash(candidate)}
            (args.output / "selection.json").write_text(json.dumps(best, indent=2))
        print(f"{label}: validation_delay={score:.3f}s best={best['score']:.3f}s ({Path(best['path']).name})", flush=True)

    try:
        budget.check("initialization")
        evaluate(save(0, "initial"), "initial", 0,
                 include_baselines=not getattr(args, "skip_initial_baselines", False))
        teacher = get_controller("max_pressure")
        for episode in range(args.demo_episodes):
            budget.check("demonstrations")
            sc = training_scenario(scenarios[episode % len(scenarios)], rng, args.episode_steps, args.domain_randomization)
            row = collect_episode(agent, sc, 100000 + args.seed * 1000 + episode,
                            training_fault(rng, not args.clean_only), 0, teacher=teacher, learn=False,
                            budget=budget, train_with_shield=args.train_with_shield)
            counts["demonstrations_completed"] += 1
            with (args.output / "demonstrations.jsonl").open("a") as stream:
                stream.write(json.dumps(row) + "\n")
            if (episode + 1) % 25 == 0:
                print(f"Demonstrations: {episode+1}/{args.demo_episodes} episodes; {len(agent.replay_buffer)} transitions", flush=True)
        for _ in range(args.imitation_updates):
            budget.check("imitation")
            if len(agent.replay_buffer) < HP.BATCH_SIZE:
                break
            batch = agent.replay_buffer.sample(HP.BATCH_SIZE)
            states, actions, masks = batch[0], batch[1], batch[7]
            logits = agent.online_net(states, valid_action_mask=masks).masked_fill(~masks, -1e9)
            loss = torch.nn.functional.cross_entropy(logits, actions)
            agent.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(agent.online_net.parameters(), 10.)
            agent.optimizer.step()
            counts["imitation_updates_completed"] += 1
        agent.sync_target_network()
        for _ in range(args.pretrain_updates):
            budget.check("pretraining")
            if len(agent.replay_buffer) < HP.BATCH_SIZE:
                break
            agent.train_step(agent.replay_buffer.sample(HP.BATCH_SIZE))
            counts["pretrain_updates_completed"] += 1
            if agent.step_count % args.target_update == 0:
                agent.sync_target_network()
        agent.sync_target_network()
        budget.check("warmup")
        print(f"Warmup complete: {len(agent.replay_buffer)} transitions, {agent.step_count} updates", flush=True)
        evaluate(save(0, "warmup"), "warmup", 0)
        epsilon_start = .25 if args.checkpoint else .8
        for episode in range(1, args.episodes + 1):
            budget.check("training")
            agent.demonstration_loss_weight = demonstration_weight(args.demo_loss_weight,
                getattr(args, "demo_loss_final_weight", None), getattr(args, "demo_loss_decay_episodes", 0), episode)
            epsilon = max(.05, epsilon_start * (.05 / epsilon_start) ** (episode / (args.episodes * .8)))
            sc = training_scenario(scenarios[int(rng.integers(len(scenarios)))], rng, args.episode_steps, args.domain_randomization)
            fixed_updates = getattr(args, "updates_per_episode", None)
            updates_before = agent.step_count
            row = collect_episode(agent, sc,
                                  500000 + args.seed * 1000 + episode,
                                  training_fault(rng, not args.clean_only), epsilon,
                                  target_update=args.target_update, budget=budget,
                                  train_with_shield=args.train_with_shield, learn=fixed_updates is None)
            if fixed_updates is not None:
                row["loss"] = fixed_episode_updates(agent, fixed_updates, args.target_update, budget)
            row.update(episode=episode, epsilon=epsilon, demonstration_loss_weight=agent.demonstration_loss_weight,
                       online_updates=agent.step_count - updates_before, total_updates=agent.step_count,
                       q_stats=agent.latest_q_stats.copy())
            episodes_completed = episode
            agent.replay_buffer.anneal_beta(episode, args.episodes)
            with (args.output / "training.jsonl").open("a") as stream:
                stream.write(json.dumps(row) + "\n")
            if episode % 20 == 0:
                print(f"Training episode={episode} epsilon={epsilon:.3f} loss={row['loss']} delay={row['avg_delay']:.3f}s", flush=True)
            if episode % args.validate_every == 0 or episode == args.episodes:
                budget.check("candidate_checkpoint")
                evaluate(save(episode, str(episode)), str(episode), episode)
    except BudgetExceeded as exc:
        stop_reason, interrupted_stage = "wall_clock_budget", str(exc)
        interrupted_checkpoint = str(save(episodes_completed, "interrupted").resolve())
        print(f"Budget reached during {interrupted_stage}; partial candidate not selected", flush=True)
    (args.output / "summary.json").write_text(json.dumps({"best": best, "elapsed_seconds": budget.elapsed,
                                                         "episodes_completed": episodes_completed, **counts,
                                                         "stop_reason": stop_reason, "interrupted_stage": interrupted_stage,
                                                         "interrupted_checkpoint": interrupted_checkpoint,
                                                         "training_seed": args.seed, "publication_ready": False}, indent=2))
    print(json.dumps(best), flush=True)


if __name__ == "__main__":
    main()
