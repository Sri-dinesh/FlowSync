#!/usr/bin/env python3
"""Collect role-separated training labels; never train, validate, or promote."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch

from research.audits.audit_policy_decisions import audit_run
from research.training.train_policy import BudgetExceeded, RunBudget, VALIDATION_FAULTS, file_hash, load_split

PROTOCOL = ROOT / "research/docs/protocols/ACTION_RANK_DATA_PROTOCOL_20261020.md"
ROLES = {"fit": tuple(range(95001, 95007)),
         "calibration": tuple(range(95101, 95111)),
         "probe": (95201, 95202)}
PARENTS = (101, 202, 303)
HORIZON = 400
MAX_EVENTS = 3


def selected_steps(source, parent, duration):
    """Outcome-blind deterministic sampling of the eligible policy gates."""
    if source["split"] != "train":
        raise ValueError("Training-only data collection")
    eligible = [e["step"] for e in source["events"]
                if sum(e["mask"]) >= 2 and e["step"] + HORIZON <= duration]
    if len(set(eligible)) != len(eligible):
        raise ValueError("Duplicate policy gate")
    key = [parent, source["scenario"], source["seed"], source["fault"]["name"]]
    def priority(step):
        return hashlib.sha256(json.dumps([*key, step]).encode()).hexdigest(), step
    return sorted(sorted(eligible, key=priority)[:MAX_EVENTS])


def verify_replay(source, branched, steps):
    """Forks must not mutate the original parent trajectory."""
    cleaned = dict(branched)
    cleaned["events"] = [{k: v for k, v in e.items()
                          if k not in ("horizon_steps", "all_action_branches")}
                         for e in branched["events"]]
    if cleaned != source:
        raise ValueError("Branching changed the source trajectory")
    events = [e for e in branched["events"] if "all_action_branches" in e]
    if sorted(e["step"] for e in events) != sorted(steps):
        raise ValueError("Incorrect selected branch gates")
    if branched["signal_samples"] != 1200 or branched["signal_violations"]:
        raise ValueError("Incomplete/unsafe source signal audit")
    for event in events:
        branches = event["all_action_branches"]
        expected = {i for i, flag in enumerate(event["mask"]) if flag}
        if (len(branches) != len(expected) or
                {b["proposal"] for b in branches} != expected or
                event["policy_proposal"] not in expected):
            raise ValueError("Missing/duplicate branch action")
        arrivals = {b["outcome"]["arrival_trace_hash"] for b in branches}
        if len(arrivals) != 1 or not next(iter(arrivals)):
            raise ValueError("Unpaired branch arrivals")
        if event["horizon_steps"] != HORIZON:
            raise ValueError("Wrong branch horizon")
        for b in branches:
            out = b["outcome"]
            values = [out[k] for k in ("incremental_delay_vehicle_seconds",
                                      "vehicles_passed", "upstream_max_wait_s")]
            if not np.isfinite(values).all() or min(values) < 0:
                raise ValueError("Invalid branch metric")
            if out["signal_samples"] != HORIZON or out["signal_violations"]:
                raise ValueError("Incomplete/unsafe branch signal audit")


def plan_cells(scenarios, smoke=False):
    if smoke:
        if "train_low_balanced_01" not in scenarios:
            raise ValueError("Smoke scenario missing")
        return [("fit", 95001, 101, "train_low_balanced_01", VALIDATION_FAULTS[0])]
    return [(role, traffic, parent, scenario, fault)
            for role, traffic_seeds in ROLES.items()
            for traffic, parent, scenario, fault in itertools.product(
                traffic_seeds, PARENTS, sorted(scenarios), VALIDATION_FAULTS)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-wall-seconds", type=float, default=3300.)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Choose a fresh output directory; previous labels are preserved")
    if not np.isfinite(args.max_wall_seconds) or args.max_wall_seconds <= 0:
        raise ValueError("A finite positive collection budget is required")
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    batch_path = args.batch / "batch_manifest.json"
    parents = json.loads(batch_path.read_text())["parents"]
    inputs = [batch_path]
    for parent in PARENTS:
        item = parents[str(parent)]
        path = Path(item["path"])
        if file_hash(path) != item["sha256"]:
            raise ValueError("Parent checkpoint changed")
        inputs.append(path)
    scenarios = {s.scenario_id: s for s in load_split("train")}
    if len(scenarios) != 6 or any(s.duration_steps != 1200 for s in scenarios.values()):
        raise ValueError("Expected six 1200-tick training templates")
    cells = plan_cells(scenarios, args.smoke)
    sources = [p for folder in (ROOT / "research", ROOT / "server/app")
               for p in sorted(folder.rglob("*.py"))]
    sources += [PROTOCOL] + sorted((ROOT / "research/scenarios/train").glob("*.yaml"))
    hashes = {str(p.resolve()): file_hash(p) for p in inputs}
    source_hashes = {str(p.relative_to(ROOT)): file_hash(p) for p in sources}
    args.output.mkdir(parents=True, exist_ok=False)
    manifest = dict(
        parents=parents, roles=ROLES, smoke=args.smoke, planned_runs=len(cells),
        horizon_steps=HORIZON, max_events=MAX_EVENTS, max_wall_seconds=args.max_wall_seconds,
        scenarios={n: s.to_dict() for n, s in scenarios.items()},
        faults=[f.to_dict() for f in VALIDATION_FAULTS],
        input_hashes=hashes, source_hashes=source_hashes,
        validation_access=False, test_access=False, fits_models=False)
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2))
    with zipfile.ZipFile(args.output / "source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as z:
        for p in sources:
            z.write(p, str(p.relative_to(ROOT)))
    budget = RunBudget(args.max_wall_seconds)
    counts = {role: 0 for role in ROLES}
    samples = branches_count = labelled_gates = eligible_gates = 0
    error = None
    try:
        for role, traffic, parent, name, fault in cells:
            budget.check("source_prescan")
            sc = scenarios[name]
            kwargs = dict(horizon=HORIZON, all_actions=True, budget=budget)
            source = audit_run(parents[str(parent)]["path"], sc, traffic, fault,
                               max_events=0, **kwargs)
            steps = selected_steps(source, parent, sc.duration_steps)
            branched = audit_run(parents[str(parent)]["path"], sc, traffic, fault,
                                 max_events=MAX_EVENTS, branch_steps=steps, **kwargs)
            verify_replay(source, branched, steps)
            if branched["checkpoint_hash"] != parents[str(parent)]["sha256"] or branched["scenario_hash"] != sc.compute_hash():
                raise ValueError("Label provenance mismatch")
            branched.update(training_seed=parent, data_role=role, selected_steps=steps)
            with (args.output / f"{role}.jsonl").open("a") as stream:
                stream.write(json.dumps(branched, allow_nan=False) + "\n")
            counts[role] += 1
            labelled_gates += len(steps)
            eligible_gates += sum(sum(e["mask"]) >= 2 and e["step"] + HORIZON <= sc.duration_steps
                                  for e in source["events"])
            samples += branched["signal_samples"]
            for event in branched["events"]:
                for b in event.get("all_action_branches", []):
                    branches_count += 1
                    samples += b["outcome"]["signal_samples"]
            if sum(counts.values()) % 12 == 0 or args.smoke:
                print(f"[{sum(counts.values())}/{len(cells)}] {role}, traffic {traffic}; "
                      f"{budget.elapsed:.1f}s elapsed", flush=True)
    except BudgetExceeded as exc:
        error = f"Budget stopped during {exc}"
    if any(file_hash(Path(p)) != digest for p, digest in hashes.items()):
        raise ValueError("Collection input changed")
    if any(file_hash(ROOT / p) != digest for p, digest in source_hashes.items()):
        raise ValueError("Source changed during collection")
    complete = sum(counts.values()) == len(cells)
    report = dict(
        complete=complete, full_dataset_complete=complete and not args.smoke, smoke=args.smoke,
        source_runs_by_role=counts, planned_runs=len(cells), labelled_gates=labelled_gates,
        eligible_gates=eligible_gates, branches=branches_count,
        labelled_source_and_branch_signal_samples=samples, signal_violations=0,
        elapsed_seconds=budget.elapsed, stop_reason=error,
        model_trained=False, publication_ready=False,
        output_hashes={f"{r}.jsonl": file_hash(args.output / f"{r}.jsonl")
                       for r in ROLES if (args.output / f"{r}.jsonl").exists()})
    (args.output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps(report, indent=2))
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
