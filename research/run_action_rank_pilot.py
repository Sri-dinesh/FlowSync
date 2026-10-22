#!/usr/bin/env python3
"""Train on branch labels, freeze correction models, evaluate separate traffic."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import torch
from research.action_rank_policy import ActionRankController, RankingModel, fit_model
from research.audit_fixed_replay import sha
from research.audit_policy_decisions import audit_run
from research.collect_action_rank_labels import summarize as verify_feasibility
from research.experiments.engine import ExperimentRunner
from research.experiments.shielded_controller import ShieldedController
from research.noise.fault_injector import PerceptionFaultInjector
from research.train_policy import BudgetExceeded, RunBudget, VALIDATION_FAULTS, load_split
from server.app.controllers import get_controller
from server.app.controllers.flowsync_uq import FlowSyncUQController

SEEDS=(101,202,303)
VALIDATION_SEEDS=(25001,25002)
VARIANTS=("mean","uncertain")
BASELINES=("max_pressure_shield","max_pressure","greedy","fixed","actuated")
PROTOCOL=ROOT/"research/docs/protocols/ACTION_RANK_PILOT_PROTOCOL_20261020.md"


def read(path):
    return json.loads(path.read_text())


def lines(path):
    return [json.loads(s) for s in path.read_text().splitlines()]


def append(path,row):
    with path.open("a") as stream:
        stream.write(json.dumps(row,allow_nan=False)+"\n")


def probe_predictions(model,rows,variant):
    choices=[]
    for row in rows:
        for e in row["events"]:
            branches=e.get("all_action_branches",[])
            if not branches:
                continue
            parent=e["policy_proposal"]
            action,_=model.choose(e["policy_observation"],e["phase"],e["phase_age"],e["q_values"],parent,e["mask"],variant)
            old=next(b["outcome"] for b in branches if b["proposal"]==parent)
            new=next(b["outcome"] for b in branches if b["proposal"]==action)
            choices.append(dict(training_seed=row["training_seed"],scenario=row["scenario"],seed=row["seed"],
                fault=row["fault"]["name"],step=e["step"],variant=variant,parent=parent,choice=action,
                delay_saved=old["incremental_delay_vehicle_seconds"]-new["incremental_delay_vehicle_seconds"],
                throughput_gained=new["vehicles_passed"]-old["vehicles_passed"],
                endpoint_wait_saved=old["upstream_max_wait_s"]-new["upstream_max_wait_s"]))
    return choices


def summarize_validation(rows,scenario_names):
    cells=list(itertools.product(scenario_names,VALIDATION_SEEDS,[f.name for f in VALIDATION_FAULTS]))
    expected={(name,seed,*cell) for name in ("parent",*VARIANTS) for seed in SEEDS for cell in cells}
    expected|={(name,None,*cell) for name in BASELINES for cell in cells}
    keys=[(r["name"],r["training_seed"],r["scenario"],r["seed"],r["fault"]) for r in rows]
    if len(keys)!=len(expected) or set(keys)!=expected:
        raise ValueError("Incomplete/duplicate validation cells")
    arrivals={}
    for r in rows:
        result=r["result"]
        key=r["scenario"],r["seed"]
        if not result["arrival_trace_hash"] or arrivals.setdefault(key,result["arrival_trace_hash"])!=result["arrival_trace_hash"]:
            raise ValueError("Unpaired validation arrivals")
        if result["safety_samples"]!=result["num_steps"] or result["safety_samples"]<=0:
            raise ValueError("Incomplete validation signal audit")
        if any(not isinstance(result[k],(float,int)) or not math.isfinite(result[k]) or result[k]<0
               for k in ("avg_delay","p95_delay","total_vehicles_passed","executed_conflict_violations","executed_clearance_violations")):
            raise ValueError("Invalid validation metrics")
    metrics=("avg_delay","p95_delay","total_vehicles_passed")
    means={name:{k:statistics.mean(r["result"][k] for r in rows if r["name"]==name) for k in metrics}
           for name in ("parent",*VARIANTS,*BASELINES)}
    checks={}
    for baseline in ("parent","max_pressure_shield"):
        checks[f"mean_delay_two_percent_better_vs_{baseline}"]=(means[baseline]["avg_delay"]>0 and
            means["uncertain"]["avg_delay"]<=means[baseline]["avg_delay"]*.98)
        checks[f"no_p95_regression_vs_{baseline}"]=means["uncertain"]["p95_delay"]<=means[baseline]["p95_delay"]
        checks[f"no_throughput_regression_vs_{baseline}"]=means["uncertain"]["total_vehicles_passed"]>=means[baseline]["total_vehicles_passed"]
    per_seed=[]
    for seed in SEEDS:
        per_seed.append(dict(seed=seed,**{name:statistics.mean(r["result"]["avg_delay"] for r in rows
            if r["name"]==name and r["training_seed"]==seed) for name in ("parent",*VARIANTS)}))
    checks["no_seed_regresses_over_one_percent"]=all(p["uncertain"]<=p["parent"]*1.01 for p in per_seed)
    corrections={name:sum(r["result"]["controller_diagnostics"].get("rank_corrections",0)
                        for r in rows if r["name"]==name) for name in VARIANTS}
    executed_changes={name:sum(r["result"]["controller_diagnostics"].get("rank_executed_changes",0)
                        for r in rows if r["name"]==name) for name in VARIANTS}
    checks["primary_correction_active"]=executed_changes["uncertain"]>0
    checks["zero_measured_signal_violations"]=all(r["result"]["executed_conflict_violations"]==0 and
        r["result"]["executed_clearance_violations"]==0 for r in rows)
    return dict(complete=True,validation_runs=len(rows),mean_metrics=means,per_parent_delays=per_seed,
        correction_counts=corrections,executed_change_counts=executed_changes,checks=checks,continue_to_expanded_validation=all(checks.values()),
        signal_samples=sum(r["result"]["safety_samples"] for r in rows),publication_ready=False,
        scope="Prespecified development validation; no significance or real-world-readiness claim")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch",type=Path)
    parser.add_argument("feasibility",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Choose a fresh pilot directory")
    torch.set_num_threads(1); torch.use_deterministic_algorithms(True)
    batch=read(args.batch/"batch_manifest.json"); old=read(args.feasibility/"manifest.json")
    cached=lines(args.feasibility/"runs.jsonl")
    if verify_feasibility(cached)!={k:v for k,v in read(args.feasibility/"report.json").items() if k!="elapsed_seconds"}:
        raise ValueError("Feasibility report mismatch")
    for path,digest in old["input_hashes"].items():
        if sha(Path(path))!=digest:
            raise ValueError("Feasibility input changed")
    with zipfile.ZipFile(args.feasibility/"source_snapshot.zip") as z:
        if any(hashlib.sha256(z.read(k)).hexdigest()!=v for k,v in old["source_hashes"].items()):
            raise ValueError("Feasibility archive mismatch")
    parents=batch["parents"]
    for seed in SEEDS:
        if parents[str(seed)]!=old["parents"][str(seed)] or sha(Path(parents[str(seed)]["path"]))!=parents[str(seed)]["sha256"]:
            raise ValueError("Different parent")
    train=load_split("train"); validation=load_split("validation")
    sources=[p for base in (ROOT/"research",ROOT/"server/app") for p in sorted(base.rglob("*.py"))]+[PROTOCOL]
    sources+=sorted((ROOT/"research/scenarios/train").glob("*.yaml"))+sorted((ROOT/"research/scenarios/validation").glob("*.yaml"))
    inputs=[args.batch/"batch_manifest.json",args.feasibility/"manifest.json",args.feasibility/"runs.jsonl",
            args.feasibility/"report.json",args.feasibility/"source_snapshot.zip"]
    hashes={**old["input_hashes"],**{str(p.resolve()):sha(p) for p in inputs}}
    args.output.mkdir(parents=True,exist_ok=False)
    manifest=dict(parents=parents,input_hashes=hashes,source_hashes={str(p.relative_to(ROOT)):sha(p) for p in sources},
        fit_seed=94001,probe_seed=94002,validation_seeds=VALIDATION_SEEDS,
        training_scenarios={s.scenario_id:s.to_dict() for s in train},
        validation_scenarios={s.scenario_id:s.to_dict() for s in validation},test_access=False,primary="uncertain")
    (args.output/"manifest.json").write_text(json.dumps(manifest,indent=2))
    with zipfile.ZipFile(args.output/"source_snapshot.zip","x",compression=zipfile.ZIP_DEFLATED) as z:
        for source in sources: z.write(source,str(source.relative_to(ROOT)))
    cache={(r["training_seed"],r["scenario"],r["seed"],r["fault"]["name"]):r for r in cached}
    budget=RunBudget(240); collected=[]; evaluated=[]; stage="collection"
    try:
        for traffic_seed in (94001,94002):
            for seed in SEEDS:
                for sc in train:
                    for fault in VALIDATION_FAULTS:
                        budget.check(stage)
                        key=seed,sc.scenario_id,traffic_seed,fault.name
                        row=cache.get(key)
                        if row is None:
                            row=audit_run(parents[str(seed)]["path"],sc,traffic_seed,fault,
                                horizon=400,max_events=3,all_actions=True,budget=budget)
                            row["training_seed"]=seed
                        if row["scenario_hash"]!=sc.compute_hash() or row["checkpoint_hash"]!=parents[str(seed)]["sha256"]:
                            raise ValueError("Label source provenance mismatch")
                        collected.append(row); append(args.output/"labels.jsonl",row)
            print(f"Collected traffic seed {traffic_seed}: {len(collected)}/72 source runs",flush=True)
        stage="fitting"; fitted={}
        for seed in SEEDS:
            fit=[r for r in collected if r["training_seed"]==seed and r["seed"]==94001]
            payload=fit_model(fit,seed,parents[str(seed)]["sha256"])
            path=args.output/f"rank_seed_{seed}.json"
            path.write_text(json.dumps(payload,indent=2,allow_nan=False)); fitted[seed]=dict(path=str(path.resolve()),sha256=sha(path))
        (args.output/"frozen_models.json").write_text(json.dumps(fitted,indent=2))
        for seed in SEEDS:
            model=RankingModel(read(Path(fitted[seed]["path"])))
            probe=[r for r in collected if r["training_seed"]==seed and r["seed"]==94002]
            for variant in VARIANTS:
                for row in probe_predictions(model,probe,variant): append(args.output/"probe_predictions.jsonl",row)
        stage="validation"; budget=RunBudget(240)
        for sc in validation:
            for traffic_seed in VALIDATION_SEEDS:
                for fault in VALIDATION_FAULTS:
                    requests=[(name,seed) for seed in SEEDS for name in ("parent",*VARIANTS)]+[(name,None) for name in BASELINES]
                    for name,seed in requests:
                        budget.check(stage)
                        if name=="parent":
                            ctrl=FlowSyncUQController(checkpoint_path=parents[str(seed)]["path"],enable_fallback=False)
                        elif name in VARIANTS:
                            ctrl=ActionRankController(parents[str(seed)]["path"],fitted[seed]["path"],name)
                        elif name=="max_pressure_shield": ctrl=ShieldedController(get_controller("max_pressure"))
                        else: ctrl=get_controller(name)
                        result=ExperimentRunner().run(ctrl,sc,traffic_seed,record_trajectory=False,
                            fault_injector=PerceptionFaultInjector(fault,seed=traffic_seed+90000))
                        row=dict(name=name,training_seed=seed,scenario=sc.scenario_id,seed=traffic_seed,
                                 fault=fault.name,result=result.to_dict(include_trajectory=False))
                        append(args.output/"validation.jsonl",row); evaluated.append(row)
                    print(f"Validated {len(evaluated)}/168 runs",flush=True)
        report=summarize_validation(evaluated,[s.scenario_id for s in validation])
        if any(sha(Path(v["path"]))!=v["sha256"] for v in fitted.values()):
            raise ValueError("Fitted model changed during evaluation")
    except BudgetExceeded as exc:
        report=dict(complete=False,stage=stage,stop_reason=str(exc),label_sources=len(collected),
                    validation_runs=len(evaluated),publication_ready=False)
    if any(sha(Path(k))!=v for k,v in hashes.items()):
        raise ValueError("Pilot inputs changed")
    report["last_stage_elapsed_seconds"]=budget.elapsed
    (args.output/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps(report,indent=2,allow_nan=False))
    return 0 if report["complete"] else 1


if __name__=="__main__":
    raise SystemExit(main())
