#!/usr/bin/env python3
"""Replay training sources unchanged while auditing upstream-only shadow packets."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch

from research.analysis.compare_joint_benefit import read_fit
from research.experiments.runtime import ObservedState, SignalAudit, apply_scenario_step, build_environment
from research.noise.fault_injector import PerceptionFaultInjector
from research.training.train_policy import VALIDATION_FAULTS, file_hash, load_split
from research.evaluation.evaluate_averaged_action_labels import write
from server.app.controllers.flowsync_uq import FlowSyncUQController
from server.app.controllers.max_pressure import MaxPressureController
from server.app.simulation.traffic_math import MOVEMENT_KEYS
from server.app.simulation.traffic_signal import PHASE_DEMAND_MOVEMENTS
from server.app.rl.observations import encode_policy_observation

PROTOCOL = ROOT / "research/docs/protocols/UPSTREAM_OBSERVATION_PROTOCOL_20261021.md"
SOURCE_SEED = 96301


def upstream_packet(intersection, original):
    """Camera-surrogate boundary only; no modifications to physical traffic."""
    packet = np.array(original, copy=True)
    if packet.shape != (28,) or not np.isfinite(packet).all():
        raise ValueError("Expected finite legacy 28-dimensional sensor packet")
    counts = intersection.get_upstream_movement_counts()
    packet[:12] = [np.tanh(counts[m] / 15.) for m in MOVEMENT_KEYS]
    return packet


def phase_demand(counts, phase):
    return sum(counts[m] for m in PHASE_DEMAND_MOVEMENTS[phase])


def empty_switch(action, context, upstream):
    return bool(context.is_decision_step and action != context.current_phase and phase_demand(upstream, action) == 0)


def verify_gate(event, observation, context, controller, action):
    diag = controller.d3qn.get_diagnostics()
    expected = dict(phase=context.current_phase, phase_age=context.time_in_phase,
        policy_proposal=diag["selected_action"], policy_execution=action, q_values=diag["q_values"],
        mask=context.valid_action_mask.tolist(), observed_queues=context.movement_queues,
        observed_phase_timers=context.phase_starvation_times,
        policy_observation=encode_policy_observation(observation, context, controller.d3qn.agent.obs_version).tolist(),
        shield_reason=controller.get_diagnostics()["override_reason"])
    # JSON normalizes the integer phase keys recorded in the prior artifact.
    if any(event[k] != v for k, v in json.loads(json.dumps(expected)).items()):
        raise ValueError("Source gate replay mismatch")


def audit_source(row, checkpoint, scenario):
    if row["split"] != "train" or row["data_role"] != "fit" or row["seed"] != SOURCE_SEED:
        raise ValueError("Designated fitting sources only")
    env, profile = build_environment(scenario)
    obs, _ = env.reset(seed=row["seed"])
    sensor, shadow = ObservedState(), ObservedState()
    legacy_teacher, upstream_teacher = MaxPressureController(), MaxPressureController()
    injector = PerceptionFaultInjector(VALIDATION_FAULTS[0], seed=row["seed"] + 90000)
    controller = FlowSyncUQController(checkpoint_path=str(checkpoint), enable_fallback=False)
    controller.reset(row["seed"])
    original_events = {e["step"]: e for e in row["events"]}
    counters = Counter(dict(ticks=0, ticks_with_excess_count=0, excess_vehicle_ticks=0,
        phantom_phase_ticks=0, starvation_status_disagreement_phase_ticks=0,
        decision_gates=0, gates_with_phantom_demand=0, gates_with_mask_difference=0,
        proposed_switches=0, proposed_empty_upstream_switches=0,
        executed_switches=0, executed_empty_upstream_switches=0,
        teacher_choice_differences=0, legacy_teacher_holds_upstream_switches=0,
        upstream_teacher_holds_legacy_switches=0))
    decisions, arrivals, audit = [], hashlib.sha256(), SignalAudit()
    for step in range(scenario.duration_steps):
        apply_scenario_step(env.intersection, profile, scenario.demand_profile, step)
        delivered, ctx = sensor.build(env, obs, step, injector)
        shadow_obs, shadow_ctx = shadow.build(env, upstream_packet(env.intersection, obs), step)
        upstream = shadow_ctx.movement_queues
        excess = sum(ctx.movement_queues[m] - upstream[m] for m in MOVEMENT_KEYS)
        if any(ctx.movement_queues[m] < upstream[m] for m in MOVEMENT_KEYS):
            raise ValueError("Upstream demand exceeds legacy demand")
        phantom = [p for p in range(4) if phase_demand(ctx.movement_queues, p) > 0 and phase_demand(upstream, p) == 0]
        counters["ticks"] += 1
        counters["ticks_with_excess_count"] += excess > 0
        counters["excess_vehicle_ticks"] += excess
        counters["phantom_phase_ticks"] += len(phantom)
        counters["starvation_status_disagreement_phase_ticks"] += sum(
            (ctx.phase_starvation_times[p] >= 45.) != (shadow_ctx.phase_starvation_times[p] >= 45.) for p in range(4))
        gate = ctx.is_decision_step and step >= controller.d3qn._next_decision_step
        action = controller.act(delivered, ctx)
        if gate:
            if step not in original_events:
                raise ValueError("Unexpected source decision")
            verify_gate(original_events[step], delivered, ctx, controller, action)
            proposal = controller.d3qn.get_diagnostics()["selected_action"]
            legacy_choice = legacy_teacher.act(delivered, ctx)
            upstream_choice = upstream_teacher.act(shadow_obs, shadow_ctx)
            counters["teacher_choice_differences"] += legacy_choice != upstream_choice
            counters["legacy_teacher_holds_upstream_switches"] += legacy_choice == ctx.current_phase and upstream_choice != ctx.current_phase
            counters["upstream_teacher_holds_legacy_switches"] += upstream_choice == ctx.current_phase and legacy_choice != ctx.current_phase
            counters["decision_gates"] += 1
            counters["gates_with_phantom_demand"] += bool(phantom)
            counters["gates_with_mask_difference"] += not np.array_equal(ctx.valid_action_mask, shadow_ctx.valid_action_mask)
            counters["proposed_switches"] += proposal != ctx.current_phase
            counters["proposed_empty_upstream_switches"] += empty_switch(proposal, ctx, upstream)
            counters["executed_switches"] += action != ctx.current_phase
            counters["executed_empty_upstream_switches"] += empty_switch(action, ctx, upstream)
            decisions.append(dict(training_seed=row["training_seed"], scenario=row["scenario"], seed=row["seed"],
                step=step, phase=ctx.current_phase, proposal=proposal, execution=action,
                legacy_teacher_choice=legacy_choice, upstream_teacher_choice=upstream_choice,
                outgoing_counts=ctx.outgoing_counts,
                queues=ctx.movement_queues, upstream_queues=upstream, phantom_phases=phantom,
                mask=ctx.valid_action_mask.tolist(), upstream_mask=shadow_ctx.valid_action_mask.tolist(),
                phase_timers=ctx.phase_starvation_times, upstream_phase_timers=shadow_ctx.phase_starvation_times,
                policy_observation=encode_policy_observation(delivered, ctx, controller.d3qn.agent.obs_version).tolist(),
                shadow_observation=encode_policy_observation(shadow_obs, shadow_ctx, controller.d3qn.agent.obs_version).tolist()))
        signal = env.intersection.signal
        before = signal.current_phase, signal.color.name, signal.time_in_phase
        obs, _, _, _, _ = env.step(action)
        audit.observe(before, signal)
        arrivals.update(json.dumps([step, env.intersection.spawner.generated_movements_last_tick]).encode())
    if ({e["step"] for e in decisions} != set(original_events)
            or arrivals.hexdigest() != row["arrival_trace_hash"]
            or env.intersection.get_avg_wait_time() != row["avg_delay"]
            or audit.samples != row["signal_samples"] or audit.conflicts + audit.clearance_violations != row["signal_violations"]):
        raise ValueError("Source trajectory replay mismatch")
    return dict(training_seed=row["training_seed"], scenario=row["scenario"], seed=row["seed"],
                counts=dict(counters), avg_delay=row["avg_delay"], arrival_trace_hash=arrivals.hexdigest(),
                signal_samples=audit.samples, signal_violations=audit.conflicts + audit.clearance_violations,
                original_replay_verified=True), decisions


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("pilot", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    torch.set_num_threads(1)
    rows = [r for r in read_fit(args.pilot) if r["seed"] == SOURCE_SEED]
    manifest = json.loads((args.pilot / "manifest.json").read_text())
    scenarios = {s.scenario_id: s for s in load_split("train")}
    args.output.mkdir(parents=True, exist_ok=False)
    sources = [f for base in (ROOT / "research", ROOT / "server/app") for f in sorted(base.rglob("*.py"))] + [PROTOCOL]
    source_hashes = {str(f.relative_to(ROOT)): file_hash(f) for f in sources}
    with zipfile.ZipFile(args.output / "source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as z:
        for f in sources:
            z.write(f, str(f.relative_to(ROOT)))
    inputs = {str((args.pilot / n).resolve()): file_hash(args.pilot / n) for n in ("fit.jsonl", "manifest.json")}
    inputs.update({v["path"]: v["sha256"] for v in manifest["parents"].values()})
    write(args.output / "manifest.json", dict(input_hashes=inputs, source_hashes=source_hashes,
        scenario_hashes={n: s.compute_hash() for n, s in scenarios.items()}, planned_sources=18,
        source_seed=SOURCE_SEED, parents=manifest["parents"], actions="unchanged legacy policy; shadow is read-only"))
    summaries = []
    with (args.output / "sources.jsonl").open("x") as run_stream, (args.output / "decisions.jsonl").open("x") as event_stream:
        for row in rows:
            summary, events = audit_source(row, manifest["parents"][str(row["training_seed"])]["path"], scenarios[row["scenario"]])
            summaries.append(summary)
            run_stream.write(json.dumps(summary, allow_nan=False) + "\n")
            run_stream.flush()
            for event in events:
                event_stream.write(json.dumps(event, allow_nan=False) + "\n")
            event_stream.flush()
            print(f"Verified source {len(summaries)}/18", flush=True)
    if any(file_hash(n) != h for n, h in inputs.items()):
        raise ValueError("Input changed during audit")
    def totals(selected):
        return {k: sum(s["counts"][k] for s in selected) for k in summaries[0]["counts"]}
    total = totals(summaries)
    result = dict(complete=len(summaries) == 18, sources=len(summaries), counts=total,
        per_parent={str(p): totals([s for s in summaries if s["training_seed"] == p]) for p in (101, 202, 303)},
        all_original_replays_verified=all(s["original_replay_verified"] for s in summaries),
        signal_samples=sum(s["signal_samples"] for s in summaries), signal_violations=sum(s["signal_violations"] for s in summaries),
        model_trained=False, controller_changed=False, publication_ready=False,
        calibration_access=False, probe_access=False, validation_access=False, final_test_access=False,
        scope="Read-only shadow observation on original training trajectories; no performance improvement measured",
        output_hashes={f.name: file_hash(f) for f in args.output.iterdir() if f.is_file()})
    write(args.output / "report.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
