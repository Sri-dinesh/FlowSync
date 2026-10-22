#!/usr/bin/env python3
"""Compare compact/full observed action features using grouped fitting-data folds."""
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

from research.action_rank_policy import RIDGE, TARGET_SCALE, action_features
from research.calibrate_action_rank import choose, read_role
from research.collect_action_rank_dataset import PARENTS, ROLES

PROTOCOL = ROOT / "research/docs/protocols/ACTION_FEATURE_PROTOCOL_20261020.md"
VARIANTS = ("compact", "full_state")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, data):
    with path.open("x") as stream:
        json.dump(data, stream, indent=2, allow_nan=False)


def features(event, candidate, variant):
    if variant not in VARIANTS:
        raise ValueError("Unknown feature map")
    obs = np.asarray(event["policy_observation"], dtype=float)
    parent = event["policy_proposal"]
    compact = action_features(obs, event["phase"], event["phase_age"],
                              event["q_values"], parent, candidate)
    if variant == "compact":
        return compact
    context = np.concatenate(([1.], obs, [min(event["phase_age"], 80.) / 40.]))
    contrast = np.eye(4)[candidate] - np.eye(4)[parent]
    return np.concatenate((compact, np.outer(contrast, context).ravel()))


def extract(rows, parent, variant):
    if not rows or any(r["split"] != "train" or r["data_role"] != "fit" or
                       r["training_seed"] != parent or r["seed"] not in ROLES["fit"] for r in rows):
        raise ValueError("Only one parent's fitting role is allowed")
    if len({r["checkpoint_hash"] for r in rows}) != 1:
        raise ValueError("Mixed parent checkpoints")
    xs, targets, meta = [], [], []
    for row in rows:
        for event in row["events"]:
            branches = event.get("all_action_branches", [])
            if not branches:
                continue
            base = next(b for b in branches if b["proposal"] == event["policy_proposal"])
            old = base["outcome"]
            for b in branches:
                if b is base:
                    continue
                out = b["outcome"]
                xs.append(features(event, b["proposal"], variant))
                targets.append([old["incremental_delay_vehicle_seconds"] - out["incremental_delay_vehicle_seconds"],
                                out["vehicles_passed"] - old["vehicles_passed"],
                                old["upstream_max_wait_s"] - out["upstream_max_wait_s"]])
                meta.append(dict(training_seed=parent, traffic_seed=row["seed"], scenario=row["scenario"],
                                 fault=row["fault"]["name"], step=event["step"],
                                 parent=event["policy_proposal"], action=b["proposal"],
                                 executed_change=b["first_execution"] != base["first_execution"]))
    x, y = np.asarray(xs), np.asarray(targets)
    if not len(x) or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("Empty/non-finite fitting features or labels")
    return x, y, meta


def fit_fold(x, y, groups, excluded):
    if (x.ndim != 2 or y.shape != (len(x), 3) or groups.shape != (len(x),)
            or set(groups) != set(ROLES["fit"]) or excluded not in ROLES["fit"]
            or not np.isfinite(x).all() or not np.isfinite(y).all()):
        raise ValueError("Invalid fitting fold")
    train = groups != excluded
    fit_x, fit_y, fit_groups = x[train], y[train], groups[train]
    unique, counts = np.unique(fit_groups, return_counts=True)
    count_map = dict(zip(unique, counts))
    weights = np.array([1. / count_map[g] for g in fit_groups])
    scale = np.maximum(np.sqrt(np.average(fit_x * fit_x, axis=0, weights=weights)), .05)
    z = fit_x / scale
    weights /= weights.mean()
    coefficients = np.linalg.solve(
        z.T @ (weights[:, None] * z) + RIDGE * np.eye(x.shape[1]),
        z.T @ (weights[:, None] * (fit_y / TARGET_SCALE)))
    return dict(excluded_seed=int(excluded), train_seeds=unique.tolist(),
                train_examples=int(train.sum()), dimensions=x.shape[1], ridge=RIDGE,
                scale=scale.tolist(), point=coefficients.tolist(), target_scale=TARGET_SCALE.tolist())


def predict(model, x):
    return (x / np.asarray(model["scale"])) @ np.asarray(model["point"]) * TARGET_SCALE


def decision_rows(predictions):
    grouped = {}
    for row in predictions:
        key = tuple(row[k] for k in ("variant", "training_seed", "traffic_seed", "scenario", "fault", "step"))
        grouped.setdefault(key, []).append(row)
    decisions = []
    for key, rows in sorted(grouped.items()):
        parent = rows[0]["parent"]
        if any(r["parent"] != parent for r in rows) or len({r["action"] for r in rows}) != len(rows):
            raise ValueError("Inconsistent/duplicate alternatives")
        selected = choose({r["action"]: r["point"] for r in rows}, parent)
        picked = next((r for r in rows if r["action"] == selected), None)
        gain = picked["actual"] if picked else [0., 0., 0.]
        decisions.append(dict(zip(("variant", "training_seed", "traffic_seed", "scenario", "fault", "step"), key),
                              parent=parent, choice=selected, changed=selected != parent,
                              executed_change=bool(picked and picked["executed_change"]),
                              actual=gain,
                              qualified=gain[0] > 1. and gain[1] >= 0. and gain[2] >= -1.,
                              harmful=gain[0] < -1. or gain[1] < 0. or gain[2] < -1.))
    return decisions


def summarize(predictions, decisions):
    cells = []
    for variant, parent, seed in itertools.product(VARIANTS, PARENTS, ROLES["fit"]):
        rows = [r for r in predictions if (r["variant"], r["training_seed"], r["traffic_seed"]) == (variant, parent, seed)]
        if not rows:
            raise ValueError("Incomplete prediction cells")
        residual = np.array([r["actual"] for r in rows]) - np.array([r["point"] for r in rows])
        cells.append(dict(variant=variant, parent=parent, seed=seed, alternatives=len(rows),
                          mae=np.mean(np.abs(residual), axis=0).tolist()))
    means = {v: np.mean([c["mae"] for c in cells if c["variant"] == v], axis=0).tolist() for v in VARIANTS}
    per_parent = {str(p): {v: np.mean([c["mae"] for c in cells if c["variant"] == v and c["parent"] == p],
                                    axis=0).tolist() for v in VARIANTS} for p in PARENTS}
    selections = {}
    for v in VARIANTS:
        rows = [r for r in decisions if r["variant"] == v]
        selections[v] = dict(
            decisions=len(rows), changed=sum(r["changed"] for r in rows),
            executed_changes=sum(r["executed_change"] for r in rows),
            qualified=sum(r["qualified"] and r["changed"] for r in rows),
            harmful=sum(r["harmful"] and r["changed"] for r in rows))
    old, new = selections["compact"], selections["full_state"]
    checks = dict(
        delay_mae_ten_percent_better=means["full_state"][0] <= .9 * means["compact"][0],
        no_throughput_mae_regression=means["full_state"][1] <= means["compact"][1],
        no_endpoint_wait_mae_regression=means["full_state"][2] <= means["compact"][2],
        no_parent_delay_mae_regression_over_two_percent=all(
            p["full_state"][0] <= p["compact"][0] * 1.02 for p in per_parent.values()),
        every_parent_active_and_beneficial=all(
            any(d["variant"] == "full_state" and d["training_seed"] == p and d["executed_change"] for d in decisions)
            and any(d["variant"] == "full_state" and d["training_seed"] == p and d["qualified"] for d in decisions)
            for p in PARENTS),
        qualified_count_not_lower=new["qualified"] >= old["qualified"],
        harmful_fraction_not_higher=(new["harmful"] * old["changed"] <= old["harmful"] * new["changed"]
                                     if old["changed"] else new["harmful"] == 0),
        qualified_fraction_not_lower=(new["qualified"] * old["changed"] >= old["qualified"] * new["changed"]
                                     if old["changed"] else True))
    return dict(complete=True, folds=len(cells), mean_cell_mae=means, per_parent_mae=per_parent,
                selections=selections, checks=checks, continue_to_rollout_validation=all(checks.values()),
                cells=cells, calibration_access=False, probe_access=False,
                validation_access=False, final_test_access=False, publication_ready=False,
                scope="Fitting-data feature comparison; errors and counterfactual choices are not full-run delay improvements",
                target_order=["delay_vehicle_seconds", "throughput_vehicles", "endpoint_wait_seconds"])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("dataset", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError("Choose a fresh output directory")
    manifest = json.loads((args.dataset / "manifest.json").read_text())
    report = json.loads((args.dataset / "report.json").read_text())
    if not report["full_dataset_complete"] or report["smoke"]:
        raise ValueError("Full collection is required")
    if sha(args.dataset / "fit.jsonl") != report["output_hashes"]["fit.jsonl"]:
        raise ValueError("Fitting data changed")
    for name, digest in manifest["input_hashes"].items():
        if sha(Path(name)) != digest:
            raise ValueError("Parent or collection input changed")
    with zipfile.ZipFile(args.dataset / "source_snapshot.zip") as z:
        if any(hashlib.sha256(z.read(name)).hexdigest() != digest for name, digest in manifest["source_hashes"].items()):
            raise ValueError("Collection archive mismatch")
    sources = [Path(__file__), PROTOCOL, ROOT / "research/action_rank_policy.py",
               ROOT / "research/calibrate_action_rank.py", ROOT / "research/collect_action_rank_dataset.py"]
    inputs = [args.dataset / n for n in ("manifest.json", "report.json", "source_snapshot.zip", "fit.jsonl")]
    hashes = {str(path.resolve()): sha(path) for path in inputs}
    args.output.mkdir(parents=True, exist_ok=False)
    write(args.output / "manifest.json", dict(input_hashes=hashes, parents=manifest["parents"],
          source_hashes={str(path.relative_to(ROOT)): sha(path) for path in sources}, feature_dimensions=[8, 160]))
    with zipfile.ZipFile(args.output / "source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as z:
        for path in sources:
            z.write(path, str(path.relative_to(ROOT)))
    rows = read_role(args.dataset, "fit", manifest)
    predictions, fitted = [], {}
    for parent in PARENTS:
        subset = [r for r in rows if r["training_seed"] == parent]
        for variant in VARIANTS:
            x, y, meta = extract(subset, parent, variant)
            groups = np.array([m["traffic_seed"] for m in meta])
            for excluded in ROLES["fit"]:
                model = fit_fold(x, y, groups, excluded)
                model.update(variant=variant, parent=parent, parent_sha256=manifest["parents"][str(parent)]["sha256"])
                path = args.output / f"fold_{parent}_{variant}_{excluded}.json"
                write(path, model)
                digest = sha(path)
                fitted[path.name] = digest
                indices = np.flatnonzero(groups == excluded)
                estimates = predict(model, x[indices])
                for i, estimate in zip(indices, estimates):
                    predictions.append(dict(meta[i], variant=variant, fold_model_sha256=digest,
                                            actual=y[i].tolist(), point=estimate.tolist()))
            print(f"Completed parent {parent}, {variant}: six excluded-seed folds", flush=True)
    decisions = decision_rows(predictions)
    result = summarize(predictions, decisions)
    for name, records in (("predictions.jsonl", predictions), ("decisions.jsonl", decisions)):
        with (args.output / name).open("x") as stream:
            for row in records:
                stream.write(json.dumps(row, allow_nan=False) + "\n")
    if any(sha(Path(name)) != digest for name, digest in hashes.items()):
        raise ValueError("Comparison input changed")
    write(args.output / "frozen_folds.json", fitted)
    write(args.output / "report.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "cells"}, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
