#!/usr/bin/env python3
"""Extend frozen teacher branches; retain the failed 20-second screen unchanged."""
import argparse
import json
from pathlib import Path
import statistics
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import torch
import numpy as np

from research.audit_arrival_label_stability import replace_future_rng
from research.audit_control_interventions import fork_state
from research.audit_spatial_inputs import STAGES, audit_source, write
from research.audit_teacher_alignment import FUTURES, NAMES, clean_event, gain, score
from research.branch_prefixes import rollout_prefixes
from research.train_policy import BudgetExceeded, RunBudget, file_hash
from server.app.controllers.d3qn import D3QNController

PROTOCOL=ROOT/"research/docs/protocols/TEACHER_HORIZON_PROTOCOL_20261022.md"
HORIZONS=(200,600)


def summarize(rows,planned,stop_reason):
    expected={(s["training_seed"],s["index"]):s for s in planned}
    keys=[(r["training_seed"],r["index"]) for r in rows]
    if len(keys)!=len(set(keys)) or not set(keys)<=set(expected): raise ValueError("Duplicate/unexpected sources")
    for row in rows:
        if row["signal_samples"]!=1200 or not row["source_replay_verified"]: raise ValueError("Incomplete source replay")
        source=expected[(row["training_seed"],row["index"])]
        gates={g["step"]:g for g in source["gates"]}
        if len(row["events"])!=len(gates) or {e["step"] for e in row["events"]}!=set(gates): raise ValueError("Missing/duplicate gates")
        for event in row["events"]:
            labels={(r,i) for r,indices in FUTURES.items() for i in indices}
            if not event["prefix_20_reproduced"] or len(event["futures"])!=16 or {(f["role"],f["replicate"]) for f in event["futures"]}!=labels:
                raise ValueError("Invalid prefix/future coverage")
            gate=gates[event["step"]]
            seeds={v["replicate"]:v["seed"] for vals in gate["future_seeds"].values() for v in vals}
            for future in event["futures"]:
                if future["arrival_seed"]!=seeds[future["replicate"]] or set(future["branches"])!=set(NAMES): raise ValueError("Changed future/candidate")
                branches=future["branches"]
                for name,branch in branches.items():
                    if branch["proposal"]!=gate["proposals"][name]: raise ValueError("Changed frozen proposal")
                    for horizon in HORIZONS:
                        outcome=branch["prefixes"][str(horizon)]
                        values=[outcome[k] for k in ("incremental_delay_vehicle_seconds","vehicles_passed","upstream_max_wait_s")]
                        if outcome["signal_samples"]!=horizon or not np.isfinite(values).all() or min(values)<0: raise ValueError("Invalid prefix metric/samples")
                unique={b["proposal"]:b for b in branches.values()}
                if any(b!=unique[b["proposal"]] for b in branches.values()): raise ValueError("Inconsistent duplicate proposal")
                if any(len({b["prefixes"][str(h)]["arrival_trace_hash"] for b in branches.values()})!=1 for h in HORIZONS): raise ValueError("Unpaired prefix arrivals")
    panels={}
    for role in (*FUTURES,"all"):
        panels[role]={}
        for horizon in HORIZONS:
            cells=[]
            for row in rows:
                for event in row["events"]:
                    for future in event["futures"]:
                        if role!="all" and future["role"]!=role: continue
                        branches=future["branches"]
                        base=branches["policy"]["prefixes"][str(horizon)]
                        new=branches["upstream_mp"]["prefixes"][str(horizon)]
                        cells.append(dict(training_seed=row["training_seed"],index=row["index"],step=event["step"],
                            gains=gain(base,new),switches_added=new["physical_switches"]-base["physical_switches"]))
            per_parent={str(seed):statistics.mean(c["gains"][0] for c in cells if c["training_seed"]==seed)
                        for seed in (101,202,303) if any(c["training_seed"]==seed for c in cells)}
            panels[role][str(horizon)]=dict(cases=len(cells),mean_gain=[statistics.mean(c["gains"][i] for c in cells) for i in range(3)] if cells else None,
                mean_switches_added=statistics.mean(c["switches_added"] for c in cells) if cells else None,
                per_parent_mean_delay_saved=per_parent,delay_harm_cases=sum(c["gains"][0]<-1e-7 for c in cells))
    distinct=[b["prefixes"]["600"] for row in rows for event in row["events"] for future in event["futures"]
              for b in {b["proposal"]:b for b in future["branches"].values()}.values()]
    if any(b["signal_samples"]!=600 for b in distinct): raise ValueError("Incomplete branch samples")
    primary=panels["all"]["600"]
    positive=bool(distinct) and primary["mean_gain"][0]>1e-7 and min(primary["mean_gain"][1:])>=-1e-7
    every_parent=set(primary["per_parent_mean_delay_saved"])=={"101","202","303"} and all(v>=-1e-7 for v in primary["per_parent_mean_delay_saved"].values())
    return dict(complete=len(rows)==len(planned) and stop_reason=="completed",sources=len(rows),
        gates=sum(len(r["events"]) for r in rows),unique_branches=len(distinct),panels=panels,
        signal_samples=sum(r["signal_samples"] for r in rows)+sum(b["signal_samples"] for b in distinct),
        signal_violations=sum(r["signal_violations"] for r in rows)+sum(b["signal_violations"] for b in distinct),
        aggregate_reversal_without_throughput_or_wait_loss=positive,every_parent_nonnegative=every_parent,
        original_20_second_screen="failed; unchanged",continue_to_training=False,publication_ready=False,
        scope="Exploratory horizon sensitivity on previously inspected training states/future streams; no independent test",stop_reason=stop_reason)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("input",type=Path)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    torch.set_num_threads(1)
    before=json.loads((args.input/"report.json").read_text())
    for name,digest in before["output_hashes"].items():
        if file_hash(args.input/name)!=digest: raise ValueError("Original artifact hash mismatch")
    frozen=json.loads((args.input/"frozen_proposals.json").read_text())
    originals=[json.loads(l) for l in (args.input/"sources.jsonl").read_text().splitlines()]
    if any(before[k]!=v for k,v in score(originals,frozen).items()): raise ValueError("Original screen does not reproduce")
    if before["continue_to_learning_pilot"] or not before["complete"]: raise ValueError("Expected completed failed screen")
    old_manifest=json.loads((args.input/"manifest.json").read_text())
    base_manifest=json.loads((Path(old_manifest["input"])/"manifest.json").read_text())
    batch=Path(base_manifest["batch"])
    inputs=dict(old_manifest["input_hashes"])
    inputs.update({str((args.input/n).resolve()):file_hash(args.input/n) for n in ("manifest.json","sources.jsonl","report.json","frozen_proposals.json")})
    if any(file_hash(Path(n))!=h for n,h in inputs.items()): raise ValueError("Original input hash mismatch")
    for source in frozen:
        if source["case"]["scenario"]["split"]!="train" or any(g["step"]+600>1200 for g in source["gates"]):
            raise ValueError("Cannot complete frozen training horizons")
    args.output.mkdir(parents=True,exist_ok=False)
    paths=[f for base in (ROOT/"research",ROOT/"server/app") for f in sorted(base.rglob("*.py"))]+[PROTOCOL]
    write(args.output/"manifest.json",dict(input=str(args.input.resolve()),input_hashes=inputs,horizons=HORIZONS,
        max_wall_seconds=180,planned_sources=9,planned_gates=sum(len(s["gates"]) for s in frozen),
        source_hashes={str(f.relative_to(ROOT)):file_hash(f) for f in paths}))
    with zipfile.ZipFile(args.output/"source_snapshot.zip","x",compression=zipfile.ZIP_DEFLATED) as archive:
        for f in paths: archive.write(f,str(f.relative_to(ROOT)))
    models,rows,budget,stop_reason={},[],RunBudget(180),"completed"
    with (args.output/"sources.jsonl").open("x") as stream:
        try:
            for entry in frozen:
                parent,index=entry["training_seed"],entry["index"]
                if parent not in models:
                    models[parent]={f"{arm}_{stage}":D3QNController(checkpoint_path=str(batch/f"{arm}_seed_{parent}"/f"checkpoint_{stage}.pt"))
                                    for arm in ("control","spatial") for stage in STAGES}
                old=next(r for r in originals if r["training_seed"]==parent and r["index"]==index)
                gates={e["step"]:e for e in old["events"]}
                selected={g["step"]:g for g in entry["gates"]}
                extended=[]
                def hook(event,env,sensor,injector,controller,context,scenario):
                    previous=gates[event["step"]]
                    if clean_event(event)!=clean_event(previous): raise ValueError("Source gate mismatch")
                    if event["step"] not in selected: return
                    futures=[]
                    for future in previous["teacher_futures"]:
                        outcomes={}
                        for name in NAMES:
                            proposal=future["branches"][name]["proposal"]
                            if proposal in outcomes: continue
                            state=fork_state(env,sensor,injector,controller)
                            replace_future_rng(state,future["arrival_seed"])
                            state[3].d3qn._held_action=proposal
                            first=state[3].safety_shield.filter_context(proposal,context).executed_action
                            prefixes=rollout_prefixes(state,scenario,event["step"],HORIZONS,first,budget)
                            if prefixes[200]!=future["branches"][name]["outcome"]: raise ValueError("Prior 20-second prefix mismatch")
                            outcomes[proposal]=dict(proposal=proposal,first_execution=first,prefixes={str(k):v for k,v in prefixes.items()})
                        branches={n:outcomes[future["branches"][n]["proposal"]] for n in NAMES}
                        if any(len({b["prefixes"][str(h)]["arrival_trace_hash"] for b in branches.values()})!=1 for h in HORIZONS):
                            raise ValueError("Unpaired extended arrivals")
                        futures.append(dict(role=future["role"],replicate=future["replicate"],arrival_seed=future["arrival_seed"],branches=branches))
                    extended.append(dict(step=event["step"],futures=futures,prefix_20_reproduced=True))
                result=audit_source(dict(entry["case"],acting="spatial"),batch/f"spatial_seed_{parent}"/"checkpoint_90.pt",
                    models[parent],branches=False,budget=budget,gate_hook=hook)
                for key in ("avg_delay","total_reward","vehicles_passed","arrival_trace_hash","signal_samples","signal_violations","shield_audit"):
                    if result[key]!=old[key]: raise ValueError("Source trajectory changed")
                if {e["step"] for e in result["events"]}!=set(gates) or {e["step"] for e in extended}!=set(selected):
                    raise ValueError("Missing source/branch gate")
                row=dict(training_seed=parent,index=index,signal_samples=result["signal_samples"],signal_violations=result["signal_violations"],
                         source_replay_verified=True,events=extended)
                rows.append(row)
                stream.write(json.dumps(row,allow_nan=False)+"\n");stream.flush()
                print(f"Teacher horizons {len(rows)}/9; {budget.elapsed:.1f}s",flush=True)
        except BudgetExceeded as exc: stop_reason=f"wall_clock_budget:{exc}"
    report=summarize(rows,frozen,stop_reason)
    if any(file_hash(Path(n))!=h for n,h in inputs.items()): raise ValueError("Inputs changed during extension")
    report.update(elapsed_seconds=budget.elapsed,output_hashes={f.name:file_hash(f) for f in args.output.iterdir() if f.is_file()})
    write(args.output/"report.json",report)
    print(json.dumps({k:v for k,v in report.items() if k!="output_hashes"},indent=2))
    if not report["complete"]: raise SystemExit(2)


if __name__=="__main__": main()
