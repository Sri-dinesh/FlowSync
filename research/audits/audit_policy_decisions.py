#!/usr/bin/env python3
"""Training-only paired audit of policy decisions, with identical shield rules.

Change one macro-action, then resume the same frozen RL continuation in both
branches. Simulator truth scores outcomes; it never enters policy observations.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import torch

from research.audits.audit_control_interventions import fork_state, rollout_branch
from research.experiments.runtime import ObservedState, SignalAudit, apply_scenario_step, build_environment
from research.noise.fault_injector import PerceptionFaultInjector
from research.training.train_policy import VALIDATION_FAULTS, file_hash, load_split
from server.app.controllers.flowsync_uq import FlowSyncUQController
from server.app.controllers.max_pressure import MaxPressureController
from server.app.rl.observations import encode_policy_observation


def alternative_branch(state, proposal, context):
    """The alternative must persist for the same macro-action hold, not one tick."""
    controller = state[3]
    controller.d3qn._held_action = proposal
    action = controller.safety_shield.filter_context(proposal, context).executed_action
    return state, action


def action_branches(env, sensor, injector, controller, context, scenario, step, horizon, original_action, budget=None):
    """All valid first proposals; preserve the parent hold schedule and future policy."""
    proposal = controller.d3qn.get_diagnostics()["selected_action"]
    outcomes = []
    for candidate, valid in enumerate(context.valid_action_mask):
        if not valid:
            continue
        if budget is not None:
            budget.check("action_branches")
        state = fork_state(env, sensor, injector, controller)
        if candidate == proposal:
            first_action = original_action
        else:
            state, first_action = alternative_branch(state, candidate, context)
        outcomes.append(dict(proposal=candidate, first_execution=first_action,
            outcome=rollout_branch(state, scenario, step, horizon, first_action)))
    if len({r["outcome"]["arrival_trace_hash"] for r in outcomes}) != 1:
        raise RuntimeError("Unpaired all-action branches")
    return outcomes


def audit_run(checkpoint, scenario, seed, fault, horizon=200, max_events=4, *, all_actions=False,
              budget=None, branch_steps=None, branch_diagnostic=None):
    if scenario.split != "train":
        raise ValueError("Policy development audit requires training scenarios")
    if horizon < 1 or max_events < 0:
        raise ValueError("Invalid audit horizon or event limit")
    if branch_steps is not None:
        if (not all_actions or len(set(branch_steps)) != len(branch_steps) or
                len(branch_steps) > max_events or
                any(not isinstance(s, int) or s < 0 or s+horizon > scenario.duration_steps
                    for s in branch_steps)):
            raise ValueError("Invalid explicit branch steps")
        branch_steps = set(branch_steps)
    env, profile = build_environment(scenario)
    obs, _ = env.reset(seed=seed)
    sensor = ObservedState()
    injector = PerceptionFaultInjector(fault, seed=seed+90000)
    controller = FlowSyncUQController(checkpoint_path=str(checkpoint), enable_fallback=False)
    controller.reset(seed)
    teacher = MaxPressureController()
    teacher.reset(seed)
    events, forks, arrivals, audit = [], 0, hashlib.sha256(), SignalAudit()
    last_fork_step = -200
    for step in range(scenario.duration_steps):
        if budget is not None:
            budget.check("action_source")
        apply_scenario_step(env.intersection, profile, scenario.demand_profile, step)
        observation, context = sensor.build(env, obs, step, injector)
        decision = context.is_decision_step and step >= controller.d3qn._next_decision_step
        action = controller.act(observation, context)
        if decision:
            policy = controller.d3qn.get_diagnostics()
            proposal = policy["selected_action"]
            teacher_proposal = teacher.act(observation, context)
            teacher_action = copy.deepcopy(controller.safety_shield).filter_context(teacher_proposal, context).executed_action
            event = dict(step=step, phase=context.current_phase, phase_age=context.time_in_phase,
                policy_proposal=proposal, teacher_proposal=teacher_proposal,
                policy_execution=action, teacher_execution=teacher_action,
                q_values=policy["q_values"], mask=context.valid_action_mask.tolist(),
                observed_queues=context.movement_queues,
                observed_phase_timers=context.phase_starvation_times,
                policy_observation=encode_policy_observation(observation, context, controller.d3qn.agent.obs_version).tolist(),
                shield_reason=controller.get_diagnostics()["override_reason"])
            scheduled = (step >= 200 and step-last_fork_step >= 200
                         if branch_steps is None else step in branch_steps)
            if (all_actions and scheduled and
                    sum(context.valid_action_mask) >= 2 and forks < max_events and step+horizon <= scenario.duration_steps):
                event.update(horizon_steps=horizon, all_action_branches=action_branches(
                    env,sensor,injector,controller,context,scenario,step,horizon,action,budget))
                if branch_diagnostic is not None:
                    # Optional research hook. It must fork before altering state;
                    # callers must verify the complete source replay afterward.
                    event["branch_diagnostic"] = branch_diagnostic(
                        env, sensor, injector, controller, context, scenario,
                        step, horizon, action, budget)
                forks += 1
                last_fork_step = step
            if not all_actions and action != teacher_action and forks < max_events and step+horizon <= scenario.duration_steps:
                reference = fork_state(env, sensor, injector, controller)
                alternate, alternate_action = alternative_branch(fork_state(env, sensor, injector, controller), teacher_proposal, context)
                kept = rollout_branch(reference, scenario, step, horizon, action)
                changed = rollout_branch(alternate, scenario, step, horizon, alternate_action)
                if kept["arrival_trace_hash"] != changed["arrival_trace_hash"]:
                    raise RuntimeError("Unpaired policy-decision branches")
                event.update(horizon_steps=horizon, policy_branch=kept, teacher_branch=changed,
                             delay_saved_by_teacher=kept["incremental_delay_vehicle_seconds"]-changed["incremental_delay_vehicle_seconds"])
                forks += 1
            events.append(event)
        signal = env.intersection.signal
        before = signal.current_phase, signal.color.name, signal.time_in_phase
        obs, _, _, _, _ = env.step(action)
        audit.observe(before, signal)
        arrivals.update(json.dumps([step, env.intersection.spawner.generated_movements_last_tick]).encode())
    if branch_steps is not None:
        realized = {e["step"] for e in events if "all_action_branches" in e}
        if realized != branch_steps:
            raise ValueError("Requested branch step was not an eligible policy gate")
    return dict(scenario=scenario.scenario_id, split=scenario.split, scenario_hash=scenario.compute_hash(),
                seed=seed, fault=fault.to_dict(), checkpoint_hash=file_hash(checkpoint),
                avg_delay=env.intersection.get_avg_wait_time(), arrival_trace_hash=arrivals.hexdigest(),
                signal_samples=audit.samples, signal_violations=audit.conflicts+audit.clearance_violations, events=events)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--selections", type=Path, nargs="+", required=True)
    p.add_argument("--seeds", type=int, nargs="+", default=[92001])
    p.add_argument("--horizon", type=int, default=200)
    p.add_argument("--max-events", type=int, default=4)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if min(args.seeds) < 0 or len(set(args.seeds)) != len(args.seeds) or args.horizon < 1 or args.max_events < 0:
        p.error("Invalid seed, horizon or event limit")
    torch.set_num_threads(1)
    choices = [json.loads(path.read_text()) for path in args.selections]
    for choice in choices:
        if file_hash(choice["path"]) != choice["sha256"]:
            raise ValueError("Selected checkpoint changed")
    scenarios = load_split("train")
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = dict(choices=choices, seeds=args.seeds, horizon=args.horizon, max_events=args.max_events,
        split="train", faults=[f.to_dict() for f in VALIDATION_FAULTS],
        scenario_hashes={s.scenario_id: s.compute_hash() for s in scenarios},
        planned_runs=len(choices)*len(scenarios)*len(args.seeds)*len(VALIDATION_FAULTS),
        source_hashes={str(path.relative_to(ROOT)): file_hash(path) for base in (ROOT/"research", ROOT/"server/app")
                       for path in sorted(base.rglob("*.py"))})
    (args.output/"manifest.json").write_text(json.dumps(manifest, indent=2))
    with zipfile.ZipFile(args.output/"source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in manifest["source_hashes"]:
            archive.write(ROOT/source, source)
        for scenario in sorted((ROOT/"research/scenarios/train").glob("*.yaml")):
            archive.write(scenario, str(scenario.relative_to(ROOT)))
    completed = 0
    with (args.output/"runs.jsonl").open("x") as stream:
        for choice in choices:
            for scenario in scenarios:
                for seed in args.seeds:
                    for fault in VALIDATION_FAULTS:
                        row = audit_run(choice["path"], scenario, seed, fault, args.horizon, args.max_events)
                        stream.write(json.dumps(row)+"\n")
                        stream.flush()
                        completed += 1
                        print(f"Policy audit {completed}/{manifest['planned_runs']}", flush=True)


if __name__ == "__main__":
    main()
