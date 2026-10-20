#!/usr/bin/env python3
"""Matched narrow/broader replay fitting on unchanged development probes."""
import argparse
import json
from pathlib import Path
import random
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch

from research.audit_fixed_replay import (SEEDS, STEPS, batch_for, bellman_targets, metrics,
    new_agent, sha, summarize as summarize_original, tensorize)
from research.compare_update_pressure_pilot import compare
from research.noise.fault_injector import FaultProfile
from research.scenarios.scenario_schema import ScenarioConfig
from research.train_policy import BudgetExceeded, RunBudget, collect_episode
from server.app.controllers import get_controller

ARMS = ("narrow", "broader")
EXTRA_ONLINE = (2, 17, 32, 47, 62, 77)
PROTOCOL = ROOT/"research/REPLAY_COVERAGE_PROTOCOL_20261017.md"


def read(path):
    return json.loads(path.read_text())


def jsonlines(path):
    return [json.loads(s) for s in path.read_text().splitlines()]


def extra_cases(directory, original):
    demos = jsonlines(directory/"demonstrations.jsonl")
    logs = jsonlines(directory/"training.jsonl")
    lookup = {r["episode"]:r for r in logs}
    if len(demos)<12 or len(lookup)!=len(logs) or not set(EXTRA_ONLINE)<=set(lookup):
        raise ValueError("Missing/duplicate additional cases")
    cases = []
    forbidden = {c["seed"] for c in original}
    for origin, selected in (("demo",demos[6:12]),("online",[lookup[e] for e in EXTRA_ONLINE])):
        for i,row in enumerate(selected):
            sc = ScenarioConfig.from_dict(row["executed_scenario"])
            if sc.split != "train":
                raise ValueError("Only training additions allowed")
            if row["seed"] in forbidden:
                raise ValueError("Overlapping/duplicate collection seed")
            forbidden.add(row["seed"])
            cases.append(dict(origin=origin, case=i, partition="fit", scenario=sc.to_dict(),
                              seed=row["seed"], fault=row["fault"]))
    return cases


def collect_extra(checkpoint, cases, budget):
    agent = new_agent(checkpoint)
    records = []
    for case in cases:
        before = len(agent.replay_buffer)
        result = collect_episode(agent,ScenarioConfig.from_dict(case["scenario"]),case["seed"],
            FaultProfile(**case["fault"]),0.,teacher=get_controller("max_pressure") if case["origin"]=="demo" else None,
            learn=False,budget=budget,train_with_shield=True)
        after = len(agent.replay_buffer)
        if after<=before or after>=agent.replay_buffer.capacity:
            raise ValueError("Empty/wrapped collection")
        records.append(dict(**case,transitions=after-before,result=result))
    if agent.step_count or any(not torch.equal(v,agent.online_net.state_dict()[k])
                              for k,v in checkpoint["online_net"].items()):
        raise ValueError("Collection altered parent")
    return tensorize(agent.replay_buffer.tree.data[:len(agent.replay_buffer)]),records


def verify_original(directory):
    manifest = read(directory/"manifest.json")
    if any(sha(Path(k))!=v for k,v in manifest["input_hashes"].items()):
        raise ValueError("Original input hash mismatch")
    with zipfile.ZipFile(directory/"source_snapshot.zip") as z:
        import hashlib
        if any(hashlib.sha256(z.read(k)).hexdigest()!=v for k,v in manifest["source_hashes"].items()):
            raise ValueError("Original source archive mismatch")
    rows = jsonlines(directory/"curves.jsonl")
    if summarize_original(rows)!={k:v for k,v in read(directory/"report.json").items() if k!="elapsed_seconds"}:
        raise ValueError("Original report does not reproduce")
    for seed in SEEDS:
        digest = sha(directory/f"seed_{seed}_dataset.pt")
        if any(r["dataset_sha256"]!=digest for r in rows if r["seed"]==seed):
            raise ValueError("Original dataset hash mismatch")
    return manifest,rows


def run_seed(seed, checkpoint, original, extra, old_rows, output, budget):
    expanded = {k:torch.cat((original["datasets"]["fit"][k],extra[k])) for k in extra}
    data = {**original["datasets"],"expanded_fit":expanded}
    parent = new_agent(checkpoint)
    labels = {part:bellman_targets(parent,d).clone() for part,d in data.items()}
    for part in ("fit","probe"):
        if not torch.equal(labels[part],original["labels"][part]):
            raise ValueError("Original target labels changed")
    with torch.no_grad():
        actions = {part:parent.online_net(d["states"],valid_action_mask=d["masks"])
                   .masked_fill(~d["masks"],-torch.inf).argmax(1) for part,d in data.items()}
    for part in ("fit","probe"):
        if not torch.equal(actions[part],original["initial_actions"][part]):
            raise ValueError("Original actions changed")
    schedules = dict(narrow=original["schedule"],broader=torch.from_numpy(
        np.random.default_rng(77000+seed).integers(len(expanded["states"]),size=(200,128))))
    path = output/f"seed_{seed}_dataset.pt"
    torch.save(dict(datasets=data,labels=labels,initial_actions=actions,schedules=schedules),path)
    digest = sha(path)
    for arm in ARMS:
        agent = new_agent(checkpoint)
        fit = "fit" if arm=="narrow" else "expanded_fit"
        for step in range(201):
            budget.check("coverage_updates")
            if step:
                loss,_ = agent.train_step(batch_for(data[fit],schedules[arm][step-1],labels[fit]))
                if not np.isfinite(loss):
                    raise ValueError("Non-finite learning loss")
            if step in STEPS:
                values = {part:metrics(agent,d,labels[part],actions[part]) for part,d in data.items()}
                if arm=="narrow":
                    expected = next(r for r in old_rows if r["seed"]==seed and
                                    r["arm"]=="fixed_labels" and r["updates"]==step)
                    if {k:values[k] for k in ("fit","probe")}!=expected["metrics"]:
                        raise ValueError("Narrow control does not exactly reproduce previous curve")
                row = dict(seed=seed,arm=arm,updates=step,dataset_sha256=digest,metrics=values)
                with (output/"curves.jsonl").open("a") as stream:
                    stream.write(json.dumps(row,allow_nan=False)+"\n")
        if any(not torch.equal(v,agent.target_net.state_dict()[k]) for k,v in checkpoint["online_net"].items()):
            raise ValueError("Fixed target network changed")
        print(f"seed={seed} arm={arm}: 200 updates complete",flush=True)
    if sha(path)!=digest:
        raise ValueError("Dataset changed during fitting")


def summarize(rows):
    expected = {(s,a,u) for s in SEEDS for a in ARMS for u in STEPS}
    if len(rows)!=len(expected) or {(r["seed"],r["arm"],r["updates"]) for r in rows}!=expected:
        raise ValueError("Incomplete/duplicate coverage curves")
    lookup = {(r["seed"],r["arm"],r["updates"]):r for r in rows}
    for seed in SEEDS:
        if lookup[seed,"narrow",0]["metrics"]!=lookup[seed,"broader",0]["metrics"]:
            raise ValueError("Unpaired initial metrics")
        if len({r["dataset_sha256"] for r in rows if r["seed"]==seed})!=1:
            raise ValueError("Unpaired dataset")
    if any(not np.isfinite(v) for r in rows for part in r["metrics"].values() for v in part.values()):
        raise ValueError("Non-finite diagnostic")
    pairs = [dict(seed=s,parent=lookup[s,"narrow",0]["metrics"]["probe"],
                  **{a:lookup[s,a,200]["metrics"]["probe"] for a in ARMS}) for s in SEEDS]
    means = {a:{k:float(np.mean([p[a][k] for p in pairs])) for k in pairs[0][a]}
             for a in ("parent",*ARMS)}
    checks = {}
    for baseline in ("parent","narrow"):
        checks[f"mean_probe_mae_five_percent_better_vs_{baseline}"] = (
            means[baseline]["fixed_label_mae"]>0 and
            means["broader"]["fixed_label_mae"]<=means[baseline]["fixed_label_mae"]*.95)
        checks[f"no_seed_probe_mae_regression_vs_{baseline}"] = all(
            p["broader"]["fixed_label_mae"]<=p[baseline]["fixed_label_mae"] for p in pairs)
        checks[f"no_mean_probe_joint_objective_regression_vs_{baseline}"] = (
            means["broader"]["frozen_joint_objective"]<=means[baseline]["frozen_joint_objective"])
    return dict(complete=True,pairs=pairs,mean_probe_metrics=means,checks=checks,
                promising_for_validation=all(checks.values()),publication_ready=False,
                scope="Reused training-development probes; not traffic performance or independent testing")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch",type=Path)
    parser.add_argument("original",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Choose a fresh diagnostic directory")
    torch.set_num_threads(1); torch.use_deterministic_algorithms(True)
    old_manifest,old_rows = verify_original(args.original)
    if compare(args.batch)!=read(args.batch/"comparison.json"):
        raise ValueError("Batch comparison does not reproduce")
    batch = read(args.batch/"batch_manifest.json")
    cases = {s:extra_cases(args.batch/f"control_seed_{s}",old_manifest["cases"][str(s)]) for s in SEEDS}
    inputs = [*args.original.glob("*.json"),*args.original.glob("*.jsonl"),
              *args.original.glob("*.pt"),args.original/"source_snapshot.zip"]
    hashes = {**old_manifest["input_hashes"],**{str(p.resolve()):sha(p) for p in inputs}}
    # Explicitly bind supplied batch paths to the original fixed-replay inputs.
    for path in [args.batch/"batch_manifest.json",args.batch/"comparison.json"]:
        if hashes.get(str(path.resolve()))!=sha(path):
            raise ValueError("Different input batch")
    sources = [p for base in (ROOT/"research",ROOT/"server/app") for p in sorted(base.rglob("*.py"))]+[PROTOCOL]
    args.output.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(args.output/"source_snapshot.zip","x",compression=zipfile.ZIP_DEFLATED) as z:
        for path in sources:
            z.write(path,str(path.relative_to(ROOT)))
    (args.output/"manifest.json").write_text(json.dumps(dict(input_hashes=hashes,cases=cases,
        source_hashes={str(p.relative_to(ROOT)):sha(p) for p in sources},max_wall_seconds=240,
        test_access=False),indent=2))
    budget = RunBudget(240)
    try:
        collected,checkpoints = {},{}
        for seed in SEEDS:
            random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
            cp = torch.load(batch["parents"][str(seed)]["path"],map_location="cpu",weights_only=True)
            extra,records = collect_extra(cp,cases[seed],budget)
            (args.output/f"seed_{seed}_collection.json").write_text(json.dumps(records,indent=2))
            collected[seed],checkpoints[seed] = extra,cp
        for seed in SEEDS:
            original = torch.load(args.original/f"seed_{seed}_dataset.pt",map_location="cpu",weights_only=True)
            run_seed(seed,checkpoints[seed],original,collected[seed],old_rows,args.output,budget)
        report = summarize(jsonlines(args.output/"curves.jsonl"))
    except BudgetExceeded as exc:
        report = dict(complete=False,stop_reason=str(exc),publication_ready=False)
    if any(sha(Path(k))!=v for k,v in hashes.items()):
        raise ValueError("Input changed during diagnostic")
    report["elapsed_seconds"] = budget.elapsed
    (args.output/"report.json").write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps(report,indent=2,allow_nan=False))
    return 0 if report["complete"] else 1


if __name__=="__main__":
    raise SystemExit(main())
