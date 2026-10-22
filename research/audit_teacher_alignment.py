#!/usr/bin/env python3
"""Frozen teacher-disagreement proposals under independent future arrival streams."""
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

from research.audit_arrival_label_stability import replace_future_rng
from research.audit_control_interventions import fork_state, rollout_branch
from research.audit_spatial_inputs import audit_source, write, SEEDS, STAGES
from research.train_policy import BudgetExceeded, RunBudget, file_hash
from research.verify_spatial_input_audit import verify
from server.app.controllers.d3qn import D3QNController

PROTOCOL = ROOT/"research/SPATIAL_TEACHER_ALIGNMENT_PLAN_20261022.md"
FUTURES = {"first": tuple(range(400, 408)), "excluded": tuple(range(408, 416))}
HORIZON = 200
EPS = 1e-7  # Floating-point comparison tolerance, not a traffic-benefit threshold.
NAMES = ("policy", "historical_mp", "upstream_mp")


def future_seed(parent, scenario, source_seed, step, replicate):
    key = ["spatial-teacher-v1", parent, scenario, source_seed, step, replicate]
    return int.from_bytes(hashlib.sha256(json.dumps(key).encode()).digest()[:8], "big")


def clean_event(event):
    return {k:v for k,v in event.items() if k not in ("branches", "branch_window", "teacher_futures")}


def freeze_sources(rows, manifest):
    selected = [r for r in rows if r["role"] == "online" and r["acting"] == "spatial"]
    expected = {(s,i) for s in SEEDS for i in (1,46,90)}
    if len(selected) != 9 or {(r["training_seed"],r["index"]) for r in selected} != expected:
        raise ValueError("Expected all nine frozen spatial training sources")
    result = []
    for row in selected:
        case = next(c for c in manifest["cases"][f"spatial_{row['training_seed']}"]
                    if c["role"] == "online" and c["index"] == row["index"])
        if case["scenario"]["split"] != "train" or case["seed"] != row["seed"]:
            raise ValueError("Only original recorded training cases allowed")
        eligible = [e for e in row["events"] if e["step"]+HORIZON <= 1200 and sum(e["mask"]) >= 2
                    and e["teacher_proposals"]["historical_mp"] != e["teacher_proposals"]["upstream_mp"]][:2]
        gates = []
        for event in eligible:
            proposals = dict(policy=event["proposal"], **event["teacher_proposals"])
            if any(not event["mask"][p] for p in proposals.values()):
                raise ValueError("Frozen teacher proposal outside the shared mask")
            seeds={role:[dict(replicate=i,seed=future_seed(row["training_seed"],case["scenario"]["scenario_id"],
                    case["seed"],event["step"],i)) for i in indices] for role,indices in FUTURES.items()}
            gates.append(dict(step=event["step"], proposals=proposals, future_seeds=seeds))
        result.append(dict(training_seed=row["training_seed"], index=row["index"], case=case, gates=gates))
    return result


def resample(event, env, sensor, injector, controller, context, scenario, parent, source_seed, proposals, budget=None):
    if tuple(proposals) != NAMES or any(not context.valid_action_mask[p] for p in proposals.values()):
        raise ValueError("Invalid frozen proposal set")
    old_rng = copy.deepcopy(env.intersection.spawner._rng.bit_generator.state)
    futures = []
    for role, indices in FUTURES.items():
        for index in indices:
            seed = future_seed(parent, scenario.scenario_id, source_seed, event["step"], index)
            outcomes = {}
            for proposal in sorted(set(proposals.values())):
                if budget:
                    budget.check("teacher_alignment_branch")
                state = fork_state(env, sensor, injector, controller)
                replace_future_rng(state, seed)
                state[3].d3qn._held_action = proposal
                first = state[3].safety_shield.filter_context(proposal, context).executed_action
                outcome = rollout_branch(state, scenario, event["step"], HORIZON, first)
                outcomes[proposal] = dict(proposal=proposal, first_execution=first, outcome=outcome)
            if len({b["outcome"]["arrival_trace_hash"] for b in outcomes.values()}) != 1:
                raise ValueError("Unpaired future arrivals")
            futures.append(dict(role=role, replicate=index, arrival_seed=seed,
                branches={name:outcomes[p] for name,p in proposals.items()}))
    if env.intersection.spawner._rng.bit_generator.state != old_rng:
        raise ValueError("Future replacement mutated source RNG")
    return futures


def gain(base, new):
    return [base["incremental_delay_vehicle_seconds"]-new["incremental_delay_vehicle_seconds"],
            new["vehicles_passed"]-base["vehicles_passed"],
            base["upstream_max_wait_s"]-new["upstream_max_wait_s"]]


def score(rows, frozen, stop_reason="completed"):
    expected = {(s["training_seed"],s["index"]):s for s in frozen}
    keys = [(r["training_seed"],r["index"]) for r in rows]
    if len(keys) != len(set(keys)) or not set(keys) <= set(expected):
        raise ValueError("Duplicate/unexpected source cells")
    samples, violations, gates = 0, 0, []
    for row in rows:
        if row["signal_samples"] != 1200 or not row["source_replay_verified"]:
            raise ValueError("Incomplete/unverified source replay")
        samples += row["signal_samples"]
        violations += row["signal_violations"]
        planned = {g["step"]:g for g in expected[(row["training_seed"],row["index"])]["gates"]}
        events = [e for e in row["events"] if "teacher_futures" in e]
        if {e["step"] for e in events} != set(planned) or len(events) != len(planned):
            raise ValueError("Missing/duplicate frozen gates")
        for event in events:
            outcomes = event["teacher_futures"]
            labels = {(r,i) for r,indices in FUTURES.items() for i in indices}
            if len(outcomes) != 16 or {(f["role"],f["replicate"]) for f in outcomes} != labels:
                raise ValueError("Wrong/duplicate future partition")
            measurements = {role:[] for role in FUTURES}
            for future in outcomes:
                seed = future_seed(row["training_seed"], expected[(row["training_seed"],row["index"])]["case"]["scenario"]["scenario_id"],
                                   row["seed"], event["step"], future["replicate"])
                if seed != future["arrival_seed"] or set(future["branches"]) != set(NAMES):
                    raise ValueError("Future seed/candidate mismatch")
                bs = future["branches"]
                for name,b in bs.items():
                    out = b["outcome"]
                    values = [out[n] for n in ("incremental_delay_vehicle_seconds", "vehicles_passed", "upstream_max_wait_s")]
                    if b["proposal"] != planned[event["step"]]["proposals"][name] or not np.isfinite(values).all() or min(values)<0:
                        raise ValueError("Invalid/changed frozen branch")
                    if out["signal_samples"] != HORIZON:
                        raise ValueError("Incomplete branch signal samples")
                if len({b["outcome"]["arrival_trace_hash"] for b in bs.values()}) != 1:
                    raise ValueError("Unpaired future arrivals")
                unique = {b["proposal"]:b for b in bs.values()}
                if any(b != unique[b["proposal"]] for b in bs.values()):
                    raise ValueError("Duplicate proposals have different outcomes")
                samples += sum(b["outcome"]["signal_samples"] for b in unique.values())
                violations += sum(b["outcome"]["signal_violations"] for b in unique.values())
                values = {name:gain(bs[name]["outcome"],bs["upstream_mp"]["outcome"]) for name in ("policy","historical_mp")}
                joint = all(min(v)>=-EPS for v in values.values())
                measurements[future["role"]].append(dict(replicate=future["replicate"], gains=values,
                    joint_nonharm=joint, strict_delay_benefit=joint and all(v[0]>EPS for v in values.values())))
            gates.append(dict(training_seed=row["training_seed"],index=row["index"],step=event["step"],
                proposals=planned[event["step"]]["proposals"], measurements=measurements))
    complete = set(keys)==set(expected) and stop_reason=="completed"
    panels = {}
    for role in FUTURES:
        items = [m for g in gates for m in g["measurements"][role]]
        panels[role] = dict(future_cases=len(items),
            comparisons={name:dict(mean_gain=np.mean([m["gains"][name] for m in items],axis=0).tolist() if items else None,
                harmful_cases=sum(min(m["gains"][name]) < -EPS for m in items)) for name in ("policy","historical_mp")},
            joint_nonharm_cases=sum(m["joint_nonharm"] for m in items),
            joint_benefit_cases=sum(m["strict_delay_benefit"] for m in items))
    excluded = panels["excluded"]["comparisons"]
    robust_gates = [g for g in gates if sum(m["joint_nonharm"] for m in g["measurements"]["excluded"])>=6
                    and any(m["strict_delay_benefit"] for m in g["measurements"]["excluded"])]
    checks = dict(complete=complete, has_eligible_gates=bool(gates), no_signal_violations=violations==0,
        positive_aggregate_delay_vs_both=bool(gates) and all(excluded[n]["mean_gain"][0]>EPS for n in excluded),
        no_aggregate_throughput_or_endpoint_wait_loss=bool(gates) and all(min(excluded[n]["mean_gain"][1:])>=-EPS for n in excluded),
        every_gate_robust=len(robust_gates)==len(gates) and bool(gates),
        each_parent_robustly_beneficial={g["training_seed"] for g in robust_gates}==set(SEEDS))
    return dict(complete=complete, sources=len(rows), eligible_gates=len(gates), planned_gates=sum(len(s["gates"]) for s in frozen),
        signal_samples=samples, signal_violations=violations, panels=panels, gates=gates, checks=checks,
        continue_to_learning_pilot=all(checks.values()), publication_ready=False, automatic_promotion=False,
        optimizer_steps=0, stop_reason=stop_reason,
        scope="Fixed teacher proposals at seen training states under disjoint future arrivals; local hindsight, not a learned controller gain")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    torch.set_num_threads(1)
    verified = verify(args.input)
    if not verified["complete"]:
        raise ValueError("Original input-use audit is incomplete")
    original_manifest = json.loads((args.input/"manifest.json").read_text())
    originals = [json.loads(l) for l in (args.input/"sources.jsonl").read_text().splitlines()]
    frozen = freeze_sources(originals,original_manifest)
    batch = Path(original_manifest["batch"])
    hashes = {str((args.input/n).resolve()):file_hash(args.input/n) for n in ("manifest.json","sources.jsonl","report.json")}
    hashes.update(original_manifest["input_hashes"])
    args.output.mkdir(parents=True,exist_ok=False)
    write(args.output/"frozen_proposals.json",frozen)
    paths = [f for base in (ROOT/"research",ROOT/"server/app") for f in sorted(base.rglob("*.py"))]+[PROTOCOL]
    manifest = dict(input=str(args.input.resolve()), input_hashes=hashes, future_partitions=FUTURES,
        frozen_proposals_sha256=file_hash(args.output/"frozen_proposals.json"), horizon=HORIZON,
        source_hashes={str(f.relative_to(ROOT)):file_hash(f) for f in paths}, max_wall_seconds=180,
        planned_sources=9, planned_gates=sum(len(s["gates"]) for s in frozen), publication_ready=False)
    write(args.output/"manifest.json",manifest)
    with zipfile.ZipFile(args.output/"source_snapshot.zip","x",compression=zipfile.ZIP_DEFLATED) as archive:
        for f in paths:
            archive.write(f,str(f.relative_to(ROOT)))
    models, rows, stop_reason, budget = {}, [], "completed", RunBudget(180)
    with (args.output/"sources.jsonl").open("x") as stream:
        try:
            for entry in frozen:
                parent,index = entry["training_seed"],entry["index"]
                if parent not in models:
                    models[parent]={f"{arm}_{stage}":D3QNController(checkpoint_path=str(batch/f"{arm}_seed_{parent}"/f"checkpoint_{stage}.pt"))
                                    for arm in ("control","spatial") for stage in STAGES}
                original=next(r for r in originals if r["role"]=="online" and r["acting"]=="spatial" and r["training_seed"]==parent and r["index"]==index)
                original_gates={e["step"]:e for e in original["events"]}
                selected={g["step"]:g for g in entry["gates"]}
                def hook(event,env,sensor,injector,controller,context,scenario):
                    if clean_event(event)!=clean_event(original_gates[event["step"]]):
                        raise ValueError("Original source gate/Q replay mismatch")
                    if event["step"] in selected:
                        event["teacher_futures"]=resample(event,env,sensor,injector,controller,context,scenario,parent,
                            entry["case"]["seed"],selected[event["step"]]["proposals"],budget)
                row=audit_source(dict(entry["case"],acting="spatial"),batch/f"spatial_seed_{parent}"/"checkpoint_90.pt",
                                 models[parent],branches=False,budget=budget,gate_hook=hook)
                for name in ("avg_delay","total_reward","vehicles_passed","arrival_trace_hash","signal_samples","signal_violations","shield_audit"):
                    if row[name]!=original[name]:
                        raise ValueError(f"Original source metric replay mismatch: {name}")
                if {e["step"] for e in row["events"]}!=set(original_gates):
                    raise ValueError("Missing original gate")
                row.update(training_seed=parent,source_replay_verified=True)
                rows.append(row)
                stream.write(json.dumps(row,allow_nan=False)+"\n")
                stream.flush()
                print(f"Teacher alignment {len(rows)}/9; {budget.elapsed:.1f}s",flush=True)
        except BudgetExceeded as exc:
            stop_reason=f"wall_clock_budget:{exc}"
    result=score(rows,frozen,stop_reason)
    if any(file_hash(Path(n))!=h for n,h in hashes.items()) or file_hash(args.output/"frozen_proposals.json")!=manifest["frozen_proposals_sha256"]:
        raise ValueError("Audit inputs or frozen proposals changed")
    result.update(elapsed_seconds=budget.elapsed,output_hashes={f.name:file_hash(f) for f in args.output.iterdir() if f.is_file()})
    write(args.output/"report.json",result)
    print(json.dumps({k:v for k,v in result.items() if k not in ("gates","output_hashes")},indent=2))
    if not result["complete"]:
        raise SystemExit(2)


if __name__=="__main__":
    main()
