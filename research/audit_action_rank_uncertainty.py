#!/usr/bin/env python3
"""Audit frozen correction uncertainty on excluded training trajectories only."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np

from research.action_rank_policy import RankingModel, TARGET_SCALE, action_features
from research.scenarios.scenario_schema import ScenarioConfig

PROTOCOL = ROOT / "research/ACTION_RANK_UNCERTAINTY_PROTOCOL_20261020.md"
SEEDS = (101, 202, 303)
METRICS = ("delay_vehicle_seconds", "throughput_vehicles", "endpoint_wait_seconds")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def qualifies(gain):
    return gain[0] > 1. and gain[1] >= 0. and gain[2] >= -1.


def score_rows(rows, models):
    """All alternatives, with no fitting or threshold changes."""
    scored, decisions = [], []
    for row in rows:
        if row["split"] != "train" or row["seed"] != 94002:
            raise ValueError("Only excluded training probe 94002 is allowed")
        model = models[row["training_seed"]]
        if row["checkpoint_hash"] != model.payload["parent_sha256"]:
            raise ValueError("Parent provenance mismatch")
        if row["signal_samples"] != 1200 or row["signal_violations"] != 0:
            raise ValueError("Incomplete/unsafe source audit")
        cluster = f"{row['training_seed']}/{row['scenario']}/{row['seed']}"
        for event in row["events"]:
            branches = event.get("all_action_branches")
            if branches is None:
                continue
            parent = event["policy_proposal"]
            wanted = {a for a, valid in enumerate(event["mask"]) if valid}
            if (len(branches) != len(wanted) or
                    {b["proposal"] for b in branches} != wanted or parent not in wanted):
                raise ValueError("Incomplete/duplicate action alternatives")
            hashes = {b["outcome"]["arrival_trace_hash"] for b in branches}
            if len(hashes) != 1 or not next(iter(hashes)):
                raise ValueError("Unpaired branch arrivals")
            for branch in branches:
                out = branch["outcome"]
                values = [out[k] for k in ("incremental_delay_vehicle_seconds",
                                          "vehicles_passed", "upstream_max_wait_s")]
                if not np.isfinite(values).all() or min(values) < 0:
                    raise ValueError("Invalid branch outcomes")
                if (event["horizon_steps"] != 400 or out["signal_samples"] != 400
                        or out["signal_violations"] != 0):
                    raise ValueError("Incomplete/unsafe branch audit")
            base = next(b["outcome"] for b in branches if b["proposal"] == parent)
            gains = {parent: [0., 0., 0.]}
            key = dict(training_seed=row["training_seed"], scenario=row["scenario"],
                       traffic_seed=row["seed"], fault=row["fault"]["name"],
                       cluster=cluster, step=event["step"], parent=parent)
            for branch in branches:
                action = branch["proposal"]
                if action == parent:
                    continue
                out = branch["outcome"]
                actual = [base["incremental_delay_vehicle_seconds"] - out["incremental_delay_vehicle_seconds"],
                          out["vehicles_passed"] - base["vehicles_passed"],
                          base["upstream_max_wait_s"] - out["upstream_max_wait_s"]]
                x = action_features(event["policy_observation"], event["phase"], event["phase_age"],
                                    event["q_values"], parent, action) / model.scale
                point = (x @ model.point) * TARGET_SCALE
                ensemble = np.einsum("f,bft->bt", x, model.ensemble) * TARGET_SCALE
                lower = np.quantile(ensemble, .1, axis=0)
                spread = np.std(ensemble, axis=0, ddof=1)
                if not all(np.isfinite(v).all() for v in (actual, point, lower, spread)):
                    raise ValueError("Non-finite predictions")
                scored.append(dict(key, action=action, actual=actual, point=point.tolist(),
                                   lower=lower.tolist(), spread=spread.tolist()))
                gains[action] = actual
            for variant in ("mean", "uncertain"):
                choice, _ = model.choose(event["policy_observation"], event["phase"], event["phase_age"],
                                         event["q_values"], parent, event["mask"], variant)
                decisions.append(dict(key, variant=variant, choice=choice, changed=choice != parent,
                                      actual=gains[choice], qualified=qualifies(gains[choice])))
    if not scored:
        raise ValueError("No probe alternatives")
    return scored, decisions


def aggregate(rows):
    actual = np.array([r["actual"] for r in rows])
    point = np.array([r["point"] for r in rows])
    lower = np.array([r["lower"] for r in rows])
    spread = np.array([r["spread"] for r in rows])
    error = np.abs(actual - point)
    metrics = {}
    for i, name in enumerate(METRICS):
        correlation = None
        if len(rows) > 1 and np.std(spread[:, i]) > 0 and np.std(error[:, i]) > 0:
            correlation = float(np.corrcoef(spread[:, i], error[:, i])[0, 1])
        metrics[name] = dict(
            mae=float(error[:, i].mean()),
            mean_bootstrap_std=float(spread[:, i].mean()),
            lower_bound_coverage=float(np.mean(actual[:, i] >= lower[:, i])),
            lower_bound_failures=int(np.sum(actual[:, i] < lower[:, i])),
            spread_absolute_error_correlation=correlation,
        )
    return dict(alternatives=len(rows), metrics=metrics,
                simultaneous_lower_coverage=float(np.mean(np.all(actual >= lower, axis=1))))


def summarize(scored, decisions, rows):
    clusters = {key: aggregate([r for r in scored if r["cluster"] == key])
                for key in sorted({r["cluster"] for r in scored})}
    selections = {}
    for variant in ("mean", "uncertain"):
        events = [d for d in decisions if d["variant"] == variant]
        changed = [d for d in events if d["changed"]]
        selections[variant] = dict(
            labelled_decisions=len(events), changed=len(changed),
            qualified=sum(d["qualified"] for d in changed),
            delay_harm_over_one=sum(d["actual"][0] < -1. for d in changed),
            throughput_loss=sum(d["actual"][1] < 0 for d in changed),
            endpoint_wait_harm_over_one=sum(d["actual"][2] < -1. for d in changed),
        )
    return dict(
        complete=True, pooled=aggregate(scored), clusters=clusters, selections=selections,
        parent_summaries={str(s): aggregate([r for r in scored if r["training_seed"] == s])
                          for s in sorted({r["training_seed"] for r in scored})},
        equal_cluster_lower_coverage={name: float(np.mean([
            c["metrics"][name]["lower_bound_coverage"] for c in clusters.values()])) for name in METRICS},
        source_runs=len(rows), distinct_traffic_seeds=sorted({r["seed"] for r in rows}),
        total_decision_gates=sum(len(r["events"]) for r in rows),
        labelled_decision_gates=len(decisions) // 2,
        labelled_step_range=[min(r["step"] for r in scored), max(r["step"] for r in scored)],
        publication_ready=False, model_changed=False, validation_access=False, test_access=False,
        caveat="Descriptive correlated training-probe rows, not calibrated predictive guarantees or independent traffic replicates",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pilot", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Choose a fresh audit directory")
    manifest = json.loads((args.pilot / "manifest.json").read_text())
    frozen = json.loads((args.pilot / "frozen_models.json").read_text())
    if manifest["fit_seed"] != 94001 or manifest["probe_seed"] != 94002:
        raise ValueError("Unexpected fit/probe separation")
    if sha(ROOT / "research/action_rank_policy.py") != manifest["source_hashes"]["research/action_rank_policy.py"]:
        raise ValueError("Ranking implementation changed since pilot")
    models, inputs = {}, [args.pilot / n for n in ("manifest.json", "frozen_models.json", "labels.jsonl")]
    for seed in SEEDS:
        item = frozen[str(seed)]
        path = Path(item["path"])
        if sha(path) != item["sha256"]:
            raise ValueError("Frozen model changed")
        model = RankingModel(json.loads(path.read_text()))
        parent = manifest["parents"][str(seed)]
        if model.payload["seed"] != seed or model.payload["parent_sha256"] != parent["sha256"]:
            raise ValueError("Model parent mismatch")
        if sha(parent["path"]) != parent["sha256"]:
            raise ValueError("Parent checkpoint changed")
        models[seed] = model
        inputs.extend((path, Path(parent["path"])))
    rows = [json.loads(s) for s in (args.pilot / "labels.jsonl").read_text().splitlines()]
    rows = [r for r in rows if r["seed"] == 94002]
    expected = set(itertools.product(SEEDS, manifest["training_scenarios"],
                                     ("clean", "validation_mixed")))
    keys = [(r["training_seed"], r["scenario"], r["fault"]["name"]) for r in rows]
    if len(keys) != len(expected) or set(keys) != expected:
        raise ValueError("Incomplete/duplicate probe cells")
    for row in rows:
        scenario = ScenarioConfig.from_dict(manifest["training_scenarios"][row["scenario"]])
        if row["scenario_hash"] != scenario.compute_hash():
            raise ValueError("Scenario provenance mismatch")
    scored, decisions = score_rows(rows, models)
    report = summarize(scored, decisions, rows)
    sources = [Path(__file__), ROOT / "research/action_rank_policy.py", PROTOCOL]
    provenance = dict(input_hashes={str(p.resolve()): sha(p) for p in inputs},
                      source_hashes={str(p.relative_to(ROOT)): sha(p) for p in sources})
    args.output.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(args.output / "source_snapshot.zip", "x") as archive:
        for p in sources:
            archive.write(p, str(p.relative_to(ROOT)))
    for name, payload in (("manifest.json", provenance), ("report.json", report)):
        (args.output / name).write_text(json.dumps(payload, indent=2, allow_nan=False))
    for name, records in (("alternatives.jsonl", scored), ("decisions.jsonl", decisions)):
        with (args.output / name).open("x") as stream:
            for row in records:
                stream.write(json.dumps(row, allow_nan=False) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "clusters"}, indent=2))


if __name__ == "__main__":
    main()
