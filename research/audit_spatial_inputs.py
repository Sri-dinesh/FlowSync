#!/usr/bin/env python3
"""Bounded training-only v9 input, proposal and short-branch diagnosis; no training."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import statistics
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch

from research.audit_control_interventions import fork_state, rollout_branch
from research.audit_training_drift import score_actions
from research.compare_spatial_pilot import ARMS, SEEDS, compare
from research.experiments.runtime import ObservedState, SignalAudit, apply_scenario_step, build_environment
from research.noise.fault_injector import FaultProfile, PerceptionFaultInjector
from research.scenarios.scenario_schema import ScenarioConfig
from research.spatial_baselines import UpstreamMaxPressureController
from research.train_policy import BudgetExceeded, RunBudget, file_hash
from server.app.controllers.d3qn import D3QNController
from server.app.controllers.flowsync_uq import FlowSyncUQController
from server.app.controllers.max_pressure import MaxPressureController
from server.app.rl.hyperparams import HyperParams
from server.app.rl.observations import SPATIAL_VERSION, encode_policy_observation

PROTOCOL = ROOT / "research/docs/audits/SPATIAL_INPUT_AUDIT_PROTOCOL_20261022.md"
EPISODES = (1, 46, 90)
DEMOS = (1, 12, 24)
STAGES = ("initial", "30", "60", "90")
WINDOWS = (200, 600)
HORIZON = 200
HP = HyperParams()
# The hinge used by DQNAgent.train_step (distinct from its loss weight).
IMITATION_MARGIN = .5


def write(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")


def load_cases(directory):
    rows = [json.loads(line) for line in (directory / "training.jsonl").read_text().splitlines()]
    demos = [json.loads(line) for line in (directory / "demonstrations.jsonl").read_text().splitlines()]
    lookup = {r["episode"]: r for r in rows}
    if len(lookup) != 90 or len(rows) != 90 or set(lookup) != set(range(1, 91)) or len(demos) != 24:
        raise ValueError("Incomplete or duplicate training/demo rows")
    cases = []
    for role, selected in (("online", [(i, lookup[i]) for i in EPISODES]),
                           ("demo", [(i, demos[i-1]) for i in DEMOS])):
        for index, row in selected:
            scenario = ScenarioConfig.from_dict(row["executed_scenario"])
            if scenario.split != "train" or scenario.duration_steps != 1200:
                raise ValueError("Only recorded 1200-tick training cases are allowed")
            cases.append(dict(role=role, index=index, scenario=scenario.to_dict(),
                              seed=row["seed"], fault=row["fault"],
                              expected_demo=row if role == "demo" else None))
    return cases, rows


def probe_networks(models, observation, context):
    """Read-only network scores; zero extension retains the delivered base/mask."""
    result = {}
    for name, model in models.items():
        encoded = encode_policy_observation(observation, context, model.agent.obs_version)
        natural = score_actions(model.agent.online_net, encoded, context.valid_action_mask)
        zero = encoded.copy()
        zero[36:] = 0.
        ablated = score_actions(model.agent.online_net, zero, context.valid_action_mask)
        q_delta = np.asarray(natural["q_values"]) - ablated["q_values"]
        # Common value shifts cannot change rankings; report relative advantages too.
        valid_delta = q_delta[np.asarray(context.valid_action_mask, dtype=bool)]
        result[name] = dict(natural=natural, zero_spatial=ablated,
                            max_abs_q_delta=float(np.abs(q_delta).max()),
                            valid_q_delta_range=float(np.ptp(valid_delta)))
    return result


def short_branches(env, sensor, injector, controller, context, scenario, step, proposals, budget=None):
    """One macro-action intervention; identical natural policy resumes afterward."""
    outcomes = {}
    for proposal in sorted(set(proposals.values())):
        if budget:
            budget.check("branches")
        if not context.valid_action_mask[proposal]:
            raise ValueError("Branch proposal outside the shared delivered mask")
        state = fork_state(env, sensor, injector, controller)
        state[3].d3qn._held_action = proposal
        first = state[3].safety_shield.filter_context(proposal, context).executed_action
        outcomes[proposal] = dict(first_execution=first,
            outcome=rollout_branch(state, scenario, step, HORIZON, first))
    if len({r["outcome"]["arrival_trace_hash"] for r in outcomes.values()}) != 1:
        raise ValueError("Unpaired branch arrivals")
    return {name: dict(proposal=proposal, **outcomes[proposal]) for name, proposal in proposals.items()}


def audit_source(case, checkpoint, models, *, branches=True, budget=None, gate_hook=None):
    scenario = ScenarioConfig.from_dict(case["scenario"])
    if scenario.split != "train":
        raise ValueError("Spatial diagnosis requires training scenarios")
    env, profile = build_environment(scenario)
    obs, _ = env.reset(seed=case["seed"])
    sensor = ObservedState(spatial=True)
    injector = PerceptionFaultInjector(FaultProfile(**case["fault"]), seed=case["seed"] + 90000)
    controller = FlowSyncUQController(checkpoint_path=str(checkpoint), enable_shield=True, enable_fallback=False)
    controller.reset(case["seed"])
    teachers = {"historical_mp": MaxPressureController(), "upstream_mp": UpstreamMaxPressureController()}
    for teacher in teachers.values():
        teacher.reset(case["seed"])
    events, used_windows, audit, arrivals, reward = [], set(), SignalAudit(), hashlib.sha256(), 0.
    for step in range(scenario.duration_steps):
        if budget:
            budget.check("source")
        apply_scenario_step(env.intersection, profile, scenario.demand_profile, step)
        delivered, context = sensor.build(env, obs, step, injector)
        gate = context.is_decision_step and step >= controller.d3qn._next_decision_step
        if case["role"] == "demo":
            if gate:
                controller.d3qn._held_action = teachers["historical_mp"].act(delivered, context)
                controller.d3qn._next_decision_step = step + round(HP.DECISION_DT / context.dt)
            proposal = controller.d3qn._held_action if context.is_decision_step else context.current_phase
            action = controller.safety_shield.filter_context(proposal, context).executed_action
        else:
            action = controller.act(delivered, context)
        if gate:
            probes = probe_networks(models, delivered, context)
            teacher_proposals = {name: teacher.act(delivered, context) for name, teacher in teachers.items()}
            if case["role"] != "demo":
                diag = controller.d3qn.get_diagnostics()
                proposal = diag["selected_action"]
                acting = probes[case["acting"] + "_90"]["natural"]
                if proposal != acting["action"] or diag["q_values"] != acting["q_values"]:
                    raise ValueError("Probe disagrees with acting policy")
            else:
                proposal = controller.d3qn._held_action
            for values in probes.values():
                for mode in ("natural", "zero_spatial"):
                    values[mode]["execution"] = copy.deepcopy(controller.safety_shield).filter_context(
                        values[mode]["action"], context).executed_action
            event = dict(step=step, phase=context.current_phase, mask=context.valid_action_mask.tolist(),
                observation=encode_policy_observation(delivered, context, SPATIAL_VERSION).tolist(),
                observation_age_ms=context.extra_telemetry.get("observation_age_ms"),
                proposal=proposal, execution=action, teacher_proposals=teacher_proposals, probes=probes)
            eligible = [w for w in WINDOWS if w not in used_windows and step >= w]
            if (branches and case["role"] == "online" and eligible and
                    step + HORIZON <= scenario.duration_steps and sum(context.valid_action_mask) >= 2):
                window = eligible[0]
                proposals = dict(policy=proposal,
                    zero_spatial=probes[case["acting"] + "_90"]["zero_spatial"]["action"], **teacher_proposals)
                event.update(branch_window=window, branches=short_branches(env, sensor, injector,
                    controller, context, scenario, step, proposals, budget))
                used_windows.add(window)
            if gate_hook is not None:
                # Diagnostic extensions must fork before mutating any runtime state.
                gate_hook(event, env, sensor, injector, controller, context, scenario)
            events.append(event)
        signal = env.intersection.signal
        before = signal.current_phase, signal.color.name, signal.time_in_phase
        obs, tick_reward, _, _, _ = env.step(action)
        reward += tick_reward
        audit.observe(before, signal)
        arrivals.update(json.dumps([step, env.intersection.spawner.generated_movements_last_tick]).encode())
    demo_verified = None
    if case["role"] == "demo":
        original = case["expected_demo"]
        if (not np.isclose(env.intersection.get_avg_wait_time(), original["avg_delay"], rtol=0, atol=1e-10)
                or not np.isclose(reward, original["reward"], rtol=0, atol=1e-10)
                or controller.safety_shield.get_audit_metrics() != original["shield_audit"]):
            raise ValueError("Recorded demonstration replay mismatch")
        demo_verified = True
    return dict(role=case["role"], index=case["index"], seed=case["seed"],
        acting=case.get("acting", "teacher"), checkpoint_hash=file_hash(checkpoint),
        avg_delay=env.intersection.get_avg_wait_time(), total_reward=reward,
        vehicles_passed=env.intersection.total_passed, arrival_trace_hash=arrivals.hexdigest(),
        signal_samples=audit.samples, signal_violations=audit.conflicts + audit.clearance_violations,
        shield_audit=controller.safety_shield.get_audit_metrics(), demo_replay_verified=demo_verified,
        missing_branch_windows=sorted(set(WINDOWS) - used_windows) if branches and case["role"] == "online" else [],
        events=events)


def weight_report(models):
    result = {}
    for name, model in models.items():
        state = model.agent.online_net.state_dict()
        initial = models[name.rsplit("_", 1)[0] + "_initial"].agent.online_net.state_dict()
        if not all(torch.isfinite(v).all() for v in state.values()):
            raise ValueError("Non-finite checkpoint weights")
        extra = state["feature_layer.0.weight"][:, 36:]
        if (name.endswith("_initial") or name.startswith("control_")) and extra.count_nonzero():
            raise ValueError("Initial/control spatial columns must remain zero")
        result[name] = dict(spatial_column_l2=float(extra.norm()), spatial_column_abs_max=float(extra.abs().max()),
            base_column_l2=float(state["feature_layer.0.weight"][:, :36].norm()),
            whole_network_l2_change=float(sum((v-initial[k]).square().sum() for k, v in state.items()).sqrt()))
    return result


def telemetry_report(rows):
    fields = ("td_loss", "unweighted_td_loss", "demo_margin_loss", "weighted_demo_loss", "demo_sample_fraction",
              "importance_weight_mean", "pre_clip_gradient_norm", "q_mean", "target_q_mean")
    if any(not np.isfinite([r["q_stats"][k] for k in fields]).all() for r in rows):
        raise ValueError("Missing/non-finite optimizer telemetry")
    return {label: {k: statistics.mean(r["q_stats"][k] for r in selected) for k in fields}
            for label, selected in (("all_90", rows), ("first_15", rows[:15]), ("last_15", rows[-15:]))}


def summarize(rows):
    groups, branch_scores = [], []
    for role, acting in (("online", "control"), ("online", "spatial"), ("demo", "teacher")):
        selected = [r for r in rows if r["role"] == role and r["acting"] == acting]
        events = [e for r in selected for e in r["events"]]
        for name in (events[0]["probes"] if events else []):
            ps = [e["probes"][name] for e in events]
            disagreement = [e for e in events if e["probes"][name]["natural"]["action"] != e["probes"][name]["zero_spatial"]["action"]]
            groups.append(dict(role=role, state_distribution=acting, model=name, gates=len(events),
                nonzero_spatial_gates=sum(any(e["observation"][36:]) for e in events),
                multiple_valid_action_gates=sum(sum(e["mask"]) >= 2 for e in events),
                spatial_changed_proposals=len(disagreement), spatial_changed_executions=sum(
                    p["natural"]["execution"] != p["zero_spatial"]["execution"] for p in ps),
                mean_max_abs_q_delta=statistics.mean(p["max_abs_q_delta"] for p in ps),
                max_abs_q_delta=max(p["max_abs_q_delta"] for p in ps),
                mean_valid_q_delta_range=statistics.mean(p["valid_q_delta_range"] for p in ps),
                mean_margin=statistics.mean(p["natural"]["margin"] for p in ps if p["natural"]["margin"] is not None)
                    if any(p["natural"]["margin"] is not None for p in ps) else None,
                historical_teacher_agreement=sum(p["natural"]["action"] == e["teacher_proposals"]["historical_mp"] for p,e in zip(ps,events)),
                upstream_teacher_agreement=sum(p["natural"]["action"] == e["teacher_proposals"]["upstream_mp"] for p,e in zip(ps,events)),
                historical_teacher_margin_violation_gates=sum(max(
                    q + (0. if a == e["teacher_proposals"]["historical_mp"] else IMITATION_MARGIN)
                    for a,q in enumerate(p["natural"]["q_values"]) if e["mask"][a])
                    > p["natural"]["q_values"][e["teacher_proposals"]["historical_mp"]] + 1e-7 for p,e in zip(ps,events))))
        for alternative in ("zero_spatial", "historical_mp", "upstream_mp"):
            pairs = [(e["branches"]["policy"], e["branches"][alternative]) for e in events if "branches" in e]
            changed = [(a,b) for a,b in pairs if a["proposal"] != b["proposal"]]
            def savings(a,b):
                return a["outcome"]["incremental_delay_vehicle_seconds"] - b["outcome"]["incremental_delay_vehicle_seconds"]
            branch_scores.append(dict(role=role, state_distribution=acting, alternative=alternative,
                gates=len(pairs), changed_proposals=len(changed),
                changed_first_execution=sum(a["first_execution"] != b["first_execution"] for a,b in pairs),
                delay_saved_vehicle_seconds_mean=statistics.mean(savings(a,b) for a,b in pairs) if pairs else None,
                changed_delay_saved_vehicle_seconds_mean=statistics.mean(savings(a,b) for a,b in changed) if changed else None,
                changed_delay_harm_cases=sum(savings(a,b) < -1e-7 for a,b in changed),
                changed_delay_benefit_cases=sum(savings(a,b) > 1e-7 for a,b in changed),
                throughput_gained=sum(b["outcome"]["vehicles_passed"] - a["outcome"]["vehicles_passed"] for a,b in pairs),
                endpoint_wait_reduced_s_mean=statistics.mean(a["outcome"]["upstream_max_wait_s"]-b["outcome"]["upstream_max_wait_s"] for a,b in pairs) if pairs else None))
    unique_branches = [b["outcome"] for r in rows for e in r["events"] if "branches" in e
                       for p,b in {b["proposal"]: b for b in e["branches"].values()}.items()]
    samples = sum(r["signal_samples"] for r in rows) + sum(b["signal_samples"] for b in unique_branches)
    violations = sum(r["signal_violations"] for r in rows) + sum(b["signal_violations"] for b in unique_branches)
    if any(r["signal_samples"] != 1200 for r in rows) or any(b["signal_samples"] != HORIZON for b in unique_branches):
        raise ValueError("Incomplete signal sample coverage")
    for seed in SEEDS:
        for index in EPISODES:
            pair = [r for r in rows if r["training_seed"] == seed and r["index"] == index and r["role"] == "online"]
            if len(pair) == 2 and len({r["arrival_trace_hash"] for r in pair}) != 1:
                raise ValueError("Source arrivals differ across arms")
    cells = [(r["training_seed"], r["role"], r["index"], r["acting"]) for r in rows]
    expected = {(s,"online",i,a) for s in SEEDS for i in EPISODES for a in ARMS} | {(s,"demo",i,"teacher") for s in SEEDS for i in DEMOS}
    if len(cells) != len(set(cells)) or not set(cells) <= expected:
        raise ValueError("Unexpected or duplicate diagnostic cells")
    return dict(complete=set(cells) == expected, sources=len(rows), unique_branches=len(unique_branches),
        branch_gates=sum("branches" in e for r in rows for e in r["events"]),
        missing_branch_windows=sum(len(r["missing_branch_windows"]) for r in rows),
        groups=groups, branch_scores=branch_scores, signal_samples=samples, signal_violations=violations,
        source_metrics=[{k:v for k,v in r.items() if k != "events"} for r in rows],
        publication_ready=False, automatic_promotion=False, optimizer_steps=0,
        scope="Seen training configurations; same-state probes and single-future local branches, not full-run gains")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(1)
    comparison = compare(args.batch)
    if comparison != json.loads((args.batch/"comparison.json").read_text()):
        raise ValueError("Saved spatial comparison does not reproduce")
    cases, telemetry, hashes, weights, models_by_seed = {}, {}, {}, {}, {}
    for seed in SEEDS:
        models_by_seed[seed] = {}
        for arm, version in ARMS.items():
            directory = args.batch/f"{arm}_seed_{seed}"
            cases[f"{arm}_{seed}"], logs = load_cases(directory)
            telemetry[f"{arm}_{seed}"] = telemetry_report(logs)
            for stage in STAGES:
                path = directory/f"checkpoint_{stage}.pt"
                model = D3QNController(checkpoint_path=str(path))
                if model.agent.obs_version != version:
                    raise ValueError("Unexpected observation version")
                models_by_seed[seed][f"{arm}_{stage}"] = model
                hashes[str(path.resolve())] = file_hash(path)
            for name in ("training.jsonl", "demonstrations.jsonl", "manifest.json"):
                path = directory/name
                hashes[str(path.resolve())] = file_hash(path)
        if cases[f"control_{seed}"] != cases[f"spatial_{seed}"]:
            raise ValueError("Recorded case configurations differ across arms")
        weights[str(seed)] = weight_report(models_by_seed[seed])
    for name in ("comparison.json", "batch_manifest.json", "source_snapshot.zip"):
        path = args.batch/name
        hashes[str(path.resolve())] = file_hash(path)
    args.output.mkdir(parents=True, exist_ok=False)
    sources = [p for base in (ROOT/"research", ROOT/"server/app") for p in sorted(base.rglob("*.py"))] + [PROTOCOL]
    write(args.output/"manifest.json", dict(batch=str(args.batch.resolve()), cases=cases, planned_sources=27,
        input_hashes=hashes, source_hashes={str(p.relative_to(ROOT)): file_hash(p) for p in sources},
        max_wall_seconds=180, horizon=HORIZON, windows=WINDOWS,
        validation_simulations=False, final_test_access=False))
    with zipfile.ZipFile(args.output/"source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sources:
            archive.write(path, str(path.relative_to(ROOT)))
    write(args.output/"weights.json", weights)
    write(args.output/"optimizer_snapshots.json", dict(telemetry=telemetry,
        scope="Last of four updates per episode only; descriptive, no causal demo ablation"))
    budget, rows, stop_reason = RunBudget(180), [], "completed"
    with (args.output/"sources.jsonl").open("x") as stream:
        try:
            for seed in SEEDS:
                for case in cases[f"control_{seed}"]:
                    for acting in (ARMS if case["role"] == "online" else ("teacher",)):
                        arm = acting if acting != "teacher" else "spatial"
                        checkpoint = args.batch/f"{arm}_seed_{seed}"/"checkpoint_90.pt"
                        row = audit_source(dict(case, acting=acting), checkpoint, models_by_seed[seed], budget=budget)
                        row["training_seed"] = seed
                        rows.append(row)
                        stream.write(json.dumps(row, allow_nan=False)+"\n")
                        stream.flush()
                        print(f"Spatial diagnosis {len(rows)}/27; elapsed {budget.elapsed:.1f}s", flush=True)
        except BudgetExceeded as exc:
            stop_reason = f"wall_clock_budget:{exc}"
    report = summarize(rows)
    report.update(stop_reason=stop_reason, elapsed_seconds=budget.elapsed)
    if any(file_hash(Path(p)) != h for p,h in hashes.items()):
        raise ValueError("Audit inputs changed during diagnosis")
    report["output_hashes"] = {p.name: file_hash(p) for p in args.output.iterdir() if p.is_file()}
    write(args.output/"report.json", report)
    print(json.dumps({k:v for k,v in report.items() if k not in ("groups", "source_metrics", "output_hashes")}, indent=2))
    if not report["complete"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
