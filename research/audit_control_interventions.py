#!/usr/bin/env python3
"""Validation/train-only, paired short-horizon audit of shield and fallback decisions.

Simulator truth is used ONLY to score/audit decisions. It is never added to the
controller observation. This is not a deployable oracle or a policy optimizer.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch

from research.experiments.runtime import ObservedState, SignalAudit, apply_scenario_step, build_environment
from research.noise.fault_injector import PerceptionFaultInjector
from research.train_policy import VALIDATION_FAULTS, file_hash, load_split
from research.uncertainty.benefit_gate import FEATURE_NAMES, observable_features
from server.app.controllers.flowsync_uq import FlowSyncUQController
from server.app.simulation.traffic_signal import PHASE_DEMAND_MOVEMENTS


def phase_wait_truth(intersection):
    """Offline diagnostic: cumulative stopped wait of vehicles still upstream.

Includes unadmitted backlog, excludes vehicles beyond the stop line. Neither
these values nor vehicle identities are given to the decision-making code.
"""
    from server.app.simulation.intersection import STOP_LINE
    result = {}
    for phase, movements in PHASE_DEMAND_MOVEMENTS.items():
        waits = [v.wait_time for m in movements for v in intersection.lanes[m]
                 if v.position <= STOP_LINE and v.state != "passed"]
        waits += [intersection.spawner._clock - arrival for m in movements
                  for arrival in intersection.spawner._pending[m]]
        result[phase] = {"upstream_vehicles": len(waits), "max_accumulated_wait_s": max(waits, default=0.),
                         "vehicles_waited_45s": sum(w >= 45. for w in waits)}
    return result


def fork_state(env, sensor, injector, controller):
    # Share only immutable inference weights/agent. Controller hold state,
    # supervisor, shield, perception and simulation RNG are copied independently.
    return copy.deepcopy((env, sensor, injector, controller),
                         {id(controller.d3qn.agent): controller.d3qn.agent})


def rollout_branch(state, scenario, start, horizon, first_action, disable_fallback=False):
    env, sensor, injector, controller = state
    if disable_fallback:
        controller.enable_fallback = False
    audit, arrivals, delay, passed = SignalAudit(), hashlib.sha256(), 0., env.intersection.total_passed
    reward_total, switches = 0., 0
    components = {}
    for offset in range(horizon):
        step = start + offset
        if offset:
            apply_scenario_step(env.intersection, env.intersection.spawner.profile, scenario.demand_profile, step)
            obs, context = sensor.build(env, env._get_obs(), step, injector)
            action = controller.act(obs, context)
        else:
            # The source trajectory has already built this tick's context and
            # advanced controller state; do not consume perception twice.
            action = first_action
        signal = env.intersection.signal
        before = signal.current_phase, signal.color.name, signal.time_in_phase
        _, reward, _, _, info = env.step(action)
        reward_total += reward
        switches += int(before[1] == "GREEN" and signal.color.name == "YELLOW")
        for key, value in info["reward_components"].items():
            components[key] = components.get(key, 0.) + value
        audit.observe(before, signal)
        delay += env.intersection._delay_this_tick
        arrivals.update(json.dumps([step, env.intersection.spawner.generated_movements_last_tick]).encode())
    return {"incremental_delay_vehicle_seconds": delay,
            "undiscounted_training_reward": reward_total, "reward_components": components,
            "physical_switches": switches,
            "vehicles_passed": env.intersection.total_passed - passed,
            "upstream_max_wait_s": max(v["max_accumulated_wait_s"] for v in phase_wait_truth(env.intersection).values()),
            "arrival_trace_hash": arrivals.hexdigest(), "signal_samples": audit.samples,
            "signal_violations": audit.conflicts + audit.clearance_violations}


def audit_run(checkpoint, calibration, scenario, seed, fault, horizon=200, max_per_kind=2):
    if scenario.split not in ("train", "validation"):
        raise ValueError("Intervention development may not access final test scenarios")
    if horizon < 1 or max_per_kind < 0:
        raise ValueError("Invalid diagnostic horizon or event limit")
    env, profile = build_environment(scenario)
    clean, _ = env.reset(seed=seed)
    sensor = ObservedState()
    injector = PerceptionFaultInjector(fault, seed=seed+90000)
    controller = FlowSyncUQController(checkpoint_path=str(checkpoint), calibration_path=str(calibration))
    controller.reset(seed)
    events, limits = [], {"shield": 0, "fallback_entry": 0}
    previous_authority, arrivals, signal_audit = "rl_active", hashlib.sha256(), SignalAudit()
    for step in range(scenario.duration_steps):
        apply_scenario_step(env.intersection, profile, scenario.demand_profile, step)
        obs, context = sensor.build(env, clean, step, injector)
        action = controller.act(obs, context)
        diag = controller.get_diagnostics()
        kinds = []
        if diag["was_overridden"]:
            kinds.append("shield")
        if diag["authority"] == "fallback_active" and previous_authority != "fallback_active":
            kinds.append("fallback_entry")
        previous_authority = diag["authority"]
        for kind in kinds:
            row = {"kind": kind, "step": step, "proposed_action": diag["proposed_action"],
                   "executed_action": action, "override_reason": diag["override_reason"],
                   "observed_phase_timers_s": dict(context.phase_starvation_times),
                   "phase_wait_truth": phase_wait_truth(env.intersection),
                   "observation_age_ms": context.extra_telemetry.get("observation_age_ms", 0.),
                   "uncertainty_score": diag["uncertainty_score"],
                   "supervisor_score": diag["supervisor_score"],
                   "stale_observation_failover": diag["stale_observation_failover"]}
            row["observable_features"] = observable_features(context, controller._last_uncertainty.score)
            if limits[kind] < max_per_kind and step+horizon <= scenario.duration_steps:
                reference = fork_state(env, sensor, injector, controller)
                alternate = fork_state(env, sensor, injector, controller)
                if kind == "shield":
                    # Omit ONLY this tick's optional shield override. The physical
                    # FSM and all future shield decisions stay enabled.
                    alternate_action = diag["proposed_action"]
                else:
                    proposed = alternate[3].d3qn.act(obs, context)
                    alternate_action = alternate[3].safety_shield.filter_context(proposed, context).executed_action
                kept = rollout_branch(reference, scenario, step, horizon, action)
                omitted = rollout_branch(alternate, scenario, step, horizon, alternate_action,
                                         disable_fallback=kind == "fallback_entry")
                if kept["arrival_trace_hash"] != omitted["arrival_trace_hash"]:
                    raise RuntimeError("Counterfactual branches did not receive paired arrivals")
                row.update(horizon_steps=horizon, intervention_kept=kept, intervention_omitted=omitted,
                           delay_saved_by_intervention_vehicle_seconds=(omitted["incremental_delay_vehicle_seconds"]-
                                                                       kept["incremental_delay_vehicle_seconds"]))
                limits[kind] += 1
            else:
                row["counterfactual_skipped"] = "event_limit_or_insufficient_remaining_horizon"
            events.append(row)
        signal = env.intersection.signal
        before = signal.current_phase, signal.color.name, signal.time_in_phase
        clean, _, _, _, _ = env.step(action)
        signal_audit.observe(before, signal)
        arrivals.update(json.dumps([step, env.intersection.spawner.generated_movements_last_tick]).encode())
    return {"scenario": scenario.scenario_id, "split": scenario.split, "scenario_hash": scenario.compute_hash(), "seed": seed,
            "fault": fault.to_dict(), "checkpoint_hash": file_hash(checkpoint),
            "avg_delay": env.intersection.get_avg_wait_time(), "arrival_trace_hash": arrivals.hexdigest(),
            "signal_samples": signal_audit.samples,
            "signal_violations": signal_audit.conflicts+signal_audit.clearance_violations,
            "events": events, "supervisor": controller.supervisor.get_audit_summary()}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--selections", type=Path, nargs="+", required=True)
    p.add_argument("--calibration", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--split", choices=("train", "validation"), default="validation")
    p.add_argument("--seeds", type=int, nargs="+", default=[21001, 21002])
    p.add_argument("--horizon", type=int, default=200)
    p.add_argument("--max-per-kind", type=int, default=2)
    args = p.parse_args()
    if args.horizon < 1 or args.max_per_kind < 0 or min(args.seeds) < 0 or len(set(args.seeds)) != len(args.seeds):
        p.error("Invalid horizon, event limit or seeds")
    torch.set_num_threads(1)
    scenarios = load_split(args.split)
    choices = [json.loads(path.read_text()) for path in args.selections]
    for choice in choices:
        if file_hash(choice["path"]) != choice["sha256"]:
            raise ValueError("Selected checkpoint changed")
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = {"arguments": {k: str(v) if isinstance(v, Path) else [str(x) for x in v] if k == "selections" else v
                              for k, v in vars(args).items()},
                "choices": choices, "calibration_sha256": file_hash(args.calibration),
                "feature_names": FEATURE_NAMES,
                "scenario_hashes": {s.scenario_id: s.compute_hash() for s in scenarios},
                "faults": [f.to_dict() for f in VALIDATION_FAULTS],
                "source_hashes": {str(path.relative_to(ROOT)): file_hash(path) for base in (ROOT/"research", ROOT/"server/app")
                                  for path in sorted(base.rglob("*.py"))},
                "scope": "First eligible events, short-horizon counterfactual diagnostics; not independent trials or a controller",
                "planned_runs": len(choices)*len(scenarios)*len(args.seeds)*len(VALIDATION_FAULTS)}
    (args.output/"manifest.json").write_text(json.dumps(manifest, indent=2))
    with zipfile.ZipFile(args.output/"source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in manifest["source_hashes"]:
            archive.write(ROOT/source, source)
        for scenario_path in sorted((ROOT/"research/scenarios"/args.split).glob("*.yaml")):
            archive.write(scenario_path, str(scenario_path.relative_to(ROOT)))
    completed = 0
    with (args.output/"runs.jsonl").open("x") as stream:
        for choice in choices:
            for scenario in scenarios:
                for seed in args.seeds:
                    for fault in VALIDATION_FAULTS:
                        row = audit_run(choice["path"], args.calibration, scenario, seed, fault, args.horizon, args.max_per_kind)
                        stream.write(json.dumps(row)+"\n")
                        stream.flush()
                        completed += 1
                        print(f"Audited {completed}/{manifest['planned_runs']}", flush=True)


if __name__ == "__main__":
    main()
