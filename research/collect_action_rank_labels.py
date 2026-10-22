#!/usr/bin/env python3
"""Training-only all-action branch labels; oracle opportunities are not policy wins."""
import argparse
import json
import math
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import torch
from research.audit_fixed_replay import sha
from research.audit_policy_decisions import audit_run
from research.train_policy import BudgetExceeded, RunBudget, VALIDATION_FAULTS, load_split

SEEDS = (101,202,303)
SCENARIOS = ("train_low_balanced_01","train_mod_balanced_01","train_platoon_burst_01")
TRAFFIC_SEED = 94001
HORIZON = 400
PROTOCOL = ROOT/"research/docs/protocols/ACTION_RANK_PROTOCOL_20261020.md"


def summarize(rows):
    expected={(s,sc,f.name) for s in SEEDS for sc in SCENARIOS for f in VALIDATION_FAULTS}
    keys=[(r["training_seed"],r["scenario"],r["fault"]["name"]) for r in rows]
    if len(keys)!=len(expected) or set(keys)!=expected:
        raise ValueError("Incomplete/duplicate label source cells")
    events=[]; branch_samples=0; branch_violations=0
    for row in rows:
        if row["split"]!="train" or row["seed"]!=TRAFFIC_SEED or row["signal_samples"]!=1200:
            raise ValueError("Invalid source split/seed/coverage")
        for event in row["events"]:
            branches=event.get("all_action_branches")
            if branches is None:
                continue
            wanted={i for i,valid in enumerate(event["mask"]) if valid}
            if len(branches)!=len(wanted) or {b["proposal"] for b in branches}!=wanted:
                raise ValueError("Incomplete/duplicate action alternatives")
            if len(event["policy_observation"])!=36 or not all(math.isfinite(x) for x in event["policy_observation"]):
                raise ValueError("Invalid observable feature vector")
            if len({b["outcome"]["arrival_trace_hash"] for b in branches})!=1:
                raise ValueError("Unpaired branch arrivals")
            for b in branches:
                outcome=b["outcome"]
                if outcome["signal_samples"]!=HORIZON or event["horizon_steps"]!=HORIZON:
                    raise ValueError("Incomplete branch signal audit")
                for metric in ("incremental_delay_vehicle_seconds","vehicles_passed","upstream_max_wait_s"):
                    if not math.isfinite(outcome[metric]) or outcome[metric]<0:
                        raise ValueError("Invalid branch metric")
                branch_samples+=outcome["signal_samples"]; branch_violations+=outcome["signal_violations"]
            parent=next(b for b in branches if b["proposal"]==event["policy_proposal"])["outcome"]
            best=min(b["outcome"]["incremental_delay_vehicle_seconds"] for b in branches)
            qualified=[b for b in branches if
                parent["incremental_delay_vehicle_seconds"]-b["outcome"]["incremental_delay_vehicle_seconds"]>1.
                and b["outcome"]["vehicles_passed"]>=parent["vehicles_passed"]
                and b["outcome"]["upstream_max_wait_s"]<=parent["upstream_max_wait_s"]+1.
                and b["outcome"]["signal_violations"]==0]
            events.append(dict(training_seed=row["training_seed"],scenario=row["scenario"],fault=row["fault"]["name"],
                step=event["step"],alternatives=len(branches),
                hindsight_delay_opportunity=parent["incremental_delay_vehicle_seconds"]-best,
                qualified_proposals=[b["proposal"] for b in qualified]))
    groups=[]
    for field,values in (("training_seed",SEEDS),("scenario",SCENARIOS),("fault",[f.name for f in VALIDATION_FAULTS])):
        for value in values:
            subset=[e for e in events if e[field]==value]
            groups.append(dict(field=field,value=value,events=len(subset),qualified=sum(bool(e["qualified_proposals"]) for e in subset)))
    return dict(complete=True,source_runs=len(rows),events=len(events),
        branches=sum(e["alternatives"] for e in events),
        events_with_delay_opportunity=sum(e["hindsight_delay_opportunity"]>1. for e in events),
        events_with_qualified_alternative=sum(bool(e["qualified_proposals"]) for e in events),
        source_signal_samples=sum(r["signal_samples"] for r in rows),
        source_signal_violations=sum(r["signal_violations"] for r in rows),
        branch_signal_samples=branch_samples,branch_signal_violations=branch_violations,
        groups=groups,event_summary=events,publication_ready=False,learned_controller_evaluated=False,
        scope="Hindsight 40-second training branches; not achievable full-run gains or a deployable oracle")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Choose a new output directory")
    torch.set_num_threads(1); torch.use_deterministic_algorithms(True)
    parents=json.loads((args.batch/"batch_manifest.json").read_text())["parents"]
    for seed in SEEDS:
        parent=parents[str(seed)]
        if sha(Path(parent["path"]))!=parent["sha256"]:
            raise ValueError("Parent changed")
    scenarios={s.scenario_id:s for s in load_split("train") if s.scenario_id in SCENARIOS}
    if set(scenarios)!=set(SCENARIOS) or any(s.duration_steps!=1200 for s in scenarios.values()):
        raise ValueError("Unexpected source scenarios")
    sources=[p for base in (ROOT/"research",ROOT/"server/app") for p in sorted(base.rglob("*.py"))]
    sources += [PROTOCOL]+[ROOT/f"research/scenarios/train/{s}.yaml" for s in SCENARIOS]
    inputs=[args.batch/"batch_manifest.json"]+[Path(parents[str(s)]["path"]) for s in SEEDS]
    hashes={str(p.resolve()):sha(p) for p in inputs}
    args.output.mkdir(parents=True,exist_ok=False)
    manifest=dict(parents=parents,input_hashes=hashes,source_hashes={str(p.relative_to(ROOT)):sha(p) for p in sources},
        scenarios={k:s.to_dict() for k,s in scenarios.items()},faults=[f.to_dict() for f in VALIDATION_FAULTS],
        traffic_seed=TRAFFIC_SEED,horizon=HORIZON,max_events=3,planned_runs=18,max_wall_seconds=240,test_access=False)
    (args.output/"manifest.json").write_text(json.dumps(manifest,indent=2))
    with zipfile.ZipFile(args.output/"source_snapshot.zip","x",compression=zipfile.ZIP_DEFLATED) as z:
        for path in sources:
            z.write(path,str(path.relative_to(ROOT)))
    budget=RunBudget(240); rows=[]
    try:
        for seed in SEEDS:
            for name in SCENARIOS:
                for fault in VALIDATION_FAULTS:
                    row=audit_run(parents[str(seed)]["path"],scenarios[name],TRAFFIC_SEED,fault,
                                  horizon=HORIZON,max_events=3,all_actions=True,budget=budget)
                    row["training_seed"]=seed
                    rows.append(row)
                    with (args.output/"runs.jsonl").open("a") as stream:
                        stream.write(json.dumps(row,allow_nan=False)+"\n")
                    print(f"Collected {len(rows)}/18 source runs",flush=True)
        report=summarize(rows)
    except BudgetExceeded as exc:
        report=dict(complete=False,stop_reason=str(exc),source_runs=len(rows),publication_ready=False)
    if any(sha(Path(p))!=v for p,v in hashes.items()):
        raise ValueError("Input changed")
    report["elapsed_seconds"]=budget.elapsed
    (args.output/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps({k:v for k,v in report.items() if k!="event_summary"},indent=2))
    return 0 if report["complete"] else 1


if __name__=="__main__":
    raise SystemExit(main())
