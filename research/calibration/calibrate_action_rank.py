#!/usr/bin/env python3
"""Fit role-separated action regressors and conservative traffic-cluster margins."""
import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np

from research.policies.action_rank_policy import FEATURES, RIDGE, TARGET_SCALE, action_features, examples
from research.datasets.collect_action_rank_dataset import PARENTS, ROLES, selected_steps, verify_replay
from research.scenarios.scenario_schema import ScenarioConfig
from research.training.train_policy import VALIDATION_FAULTS

PROTOCOL = ROOT / "research/docs/protocols/ACTION_RANK_CALIBRATION_PROTOCOL_20261020.md"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, payload):
    with path.open("x") as stream:
        json.dump(payload, stream, indent=2, allow_nan=False)


def role_arrays(rows, role, parent, digest):
    if not rows or any(r["data_role"] != role or r["split"] != "train" or
                       r["training_seed"] != parent or r["checkpoint_hash"] != digest
                       for r in rows):
        raise ValueError("Wrong role/split/parent")
    if {r["seed"] for r in rows} != set(ROLES[role]):
        raise ValueError("Incomplete or leaking traffic-seed role")
    x, y, source_groups = examples(rows)
    # examples() emits scenario/traffic_seed/fault for each alternative.
    groups = np.array([int(g.split("/")[-2]) for g in source_groups])
    if set(groups) != set(ROLES[role]):
        raise ValueError("A traffic group has no usable alternatives")
    return x, y, groups


def fit_point(rows, parent, digest):
    x, y, groups = role_arrays(rows, "fit", parent, digest)
    unique, counts = np.unique(groups, return_counts=True)
    count_map = dict(zip(unique, counts))
    weights = np.array([1. / count_map[g] for g in groups])
    scale = np.maximum(np.sqrt(np.average(x * x, axis=0, weights=weights)), .05)
    z = x / scale
    weights /= weights.mean()
    point = np.linalg.solve(z.T @ (weights[:, None] * z) + RIDGE * np.eye(len(FEATURES)),
                            z.T @ (weights[:, None] * (y / TARGET_SCALE)))
    return dict(version="action_rank_residual_v1", parent_sha256=digest, seed=parent,
                features=list(FEATURES), scale=scale.tolist(), point=point.tolist(),
                target_scale=TARGET_SCALE.tolist(), ridge=RIDGE,
                fit_examples=len(x), fit_traffic_seeds=unique.tolist(),
                weight_group="whole_traffic_seed", calibrated=False)


def predictions(payload, x):
    return (np.asarray(x) / np.asarray(payload["scale"])) @ np.asarray(payload["point"]) * TARGET_SCALE


def residual_margin(point, actual, groups):
    if (point.shape != actual.shape or point.ndim != 2 or point.shape[1] != 3
            or groups.shape != (len(point),) or not len(point)
            or not np.isfinite(point).all() or not np.isfinite(actual).all()):
        raise ValueError("Invalid calibration arrays")
    residual = (point - actual) / TARGET_SCALE
    scores = {int(g): max(0., float(np.max(residual[groups == g]))) for g in np.unique(groups)}
    rank = math.ceil(.9 * (len(scores) + 1))
    if rank > len(scores):
        raise ValueError("Insufficient calibration traffic groups for fixed rank")
    margin = sorted(scores.values())[rank - 1]
    return margin, scores, rank


def calibrate(payload, rows):
    if payload["calibrated"]:
        raise ValueError("Already calibrated")
    x, y, groups = role_arrays(rows, "calibration", payload["seed"], payload["parent_sha256"])
    margin, scores, rank = residual_margin(predictions(payload, x), y, groups)
    return dict(payload, calibrated=True, normalized_margin=margin,
                calibration_group_scores=scores, calibration_rank=rank,
                calibration_examples=len(x), calibration_traffic_seeds=sorted(scores),
                calibration_reference=.9,
                scope="Sampled parent-policy branches; no real-world or corrected-policy guarantee")


def choose(gains, parent):
    qualifying = [a for a, g in gains.items() if g[0] > 1. and g[1] >= 0. and g[2] >= -1.]
    return max(qualifying, key=lambda a: (gains[a][0], -a)) if qualifying else parent


def probe_predictions(payload, rows):
    if not payload["calibrated"]:
        raise ValueError("Probe requires frozen calibrated model")
    role_arrays(rows, "probe", payload["seed"], payload["parent_sha256"])
    alternatives, decisions = [], []
    for row in rows:
        for event in row["events"]:
            branches = event.get("all_action_branches", [])
            if not branches:
                continue
            parent = event["policy_proposal"]
            base_branch = next(b for b in branches if b["proposal"] == parent)
            base = base_branch["outcome"]
            actuals = {parent: [0., 0., 0.]}
            executions = {b["proposal"]: b["first_execution"] for b in branches}
            means, lowers = {}, {}
            key = dict(training_seed=row["training_seed"], traffic_seed=row["seed"],
                       scenario=row["scenario"], fault=row["fault"]["name"],
                       step=event["step"], parent=parent)
            for b in branches:
                a = b["proposal"]
                if a == parent:
                    continue
                out = b["outcome"]
                gain = [base["incremental_delay_vehicle_seconds"] - out["incremental_delay_vehicle_seconds"],
                        out["vehicles_passed"] - base["vehicles_passed"],
                        base["upstream_max_wait_s"] - out["upstream_max_wait_s"]]
                x = action_features(event["policy_observation"], event["phase"], event["phase_age"],
                                    event["q_values"], parent, a)
                mean = predictions(payload, x)
                lower = mean - payload["normalized_margin"] * TARGET_SCALE
                means[a], lowers[a], actuals[a] = mean, lower, gain
                alternatives.append(dict(key, action=a, actual=gain, point=mean.tolist(), lower=lower.tolist()))
            for variant, gains in (("mean", means), ("calibrated", lowers)):
                action = choose(gains, parent)
                gain = actuals[action]
                decisions.append(dict(key, variant=variant, choice=action, actual=gain,
                    changed=action != parent, executed_change=executions[action] != executions[parent],
                    qualified=gain[0] > 1. and gain[1] >= 0. and gain[2] >= -1.,
                    harmful=gain[0] < -1. or gain[1] < 0. or gain[2] < -1.))
    return alternatives, decisions


def summarize(alternatives, decisions):
    def metrics(rows):
        actual = np.array([r["actual"] for r in rows])
        mean = np.array([r["point"] for r in rows])
        lower = np.array([r["lower"] for r in rows])
        covered = np.all(actual >= lower, axis=1)
        return dict(alternatives=len(rows), mae=np.mean(np.abs(actual - mean), axis=0).tolist(),
                    component_lower_coverage=np.mean(actual >= lower, axis=0).tolist(),
                    joint_alternative_coverage=float(np.mean(covered)),
                    fully_covered_traffic_seeds={str(g): bool(np.all(
                        covered[[r["traffic_seed"] == g for r in rows]]))
                        for g in sorted({r["traffic_seed"] for r in rows})})
    per_parent = {str(p): metrics([r for r in alternatives if r["training_seed"] == p]) for p in PARENTS}
    selections = {}
    for variant in ("mean", "calibrated"):
        selections[variant] = {}
        for parent in PARENTS:
            rows = [r for r in decisions if r["training_seed"] == parent and r["variant"] == variant]
            selections[variant][str(parent)] = dict(
                decisions=len(rows), proposal_changes=sum(r["changed"] for r in rows),
                first_execution_changes=sum(r["executed_change"] for r in rows),
                qualified_changes=sum(r["qualified"] and r["changed"] for r in rows),
                harmful_changes=sum(r["harmful"] and r["changed"] for r in rows))
    checks = dict(
        every_parent_active=all(s["first_execution_changes"] > 0 for s in selections["calibrated"].values()),
        every_parent_has_qualified_benefit=all(s["qualified_changes"] > 0 for s in selections["calibrated"].values()),
        no_selected_harm=all(s["harmful_changes"] == 0 for s in selections["calibrated"].values()),
        all_probe_traffic_groups_covered=all(all(p["fully_covered_traffic_seeds"].values()) for p in per_parent.values()))
    return dict(complete=True, pooled=metrics(alternatives), per_parent=per_parent,
                selections=selections, checks=checks,
                continue_to_rollout_validation=all(checks.values()),
                publication_ready=False, dqn_retrained=False,
                validation_access=False, test_access=False, production_changed=False,
                target_order=["delay_vehicle_seconds", "throughput_vehicles", "endpoint_wait_seconds"])


def read_role(dataset, role, manifest):
    rows = [json.loads(s) for s in (dataset / f"{role}.jsonl").read_text().splitlines()]
    faults = {f.name: f.to_dict() for f in VALIDATION_FAULTS}
    expected = set(itertools.product(ROLES[role], PARENTS, manifest["scenarios"], faults))
    keys = [(r["seed"], r["training_seed"], r["scenario"], r["fault"]["name"]) for r in rows]
    if len(keys) != len(expected) or set(keys) != expected:
        raise ValueError("Missing/duplicate role cells")
    for row in rows:
        if (row["data_role"] != role or row["split"] != "train" or
                row["checkpoint_hash"] != manifest["parents"][str(row["training_seed"])]["sha256"] or
                row["fault"] != faults[row["fault"]["name"]] or
                row["scenario_hash"] != ScenarioConfig.from_dict(manifest["scenarios"][row["scenario"]]).compute_hash()):
            raise ValueError("Role provenance mismatch")
        if row["selected_steps"] != selected_steps(row, row["training_seed"], 1200):
            raise ValueError("Gate selection mismatch")
        branched = {k: v for k, v in row.items() if k not in ("training_seed", "data_role", "selected_steps")}
        # Structural checks only: actual independent pre-scan equality was
        # checked by the collector; pre-scan records were not separately saved.
        source = dict(branched, events=[{k: v for k, v in e.items()
                      if k not in ("horizon_steps", "all_action_branches")} for e in row["events"]])
        verify_replay(source, branched, row["selected_steps"])
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Choose a fresh calibration directory")
    manifest = json.loads((args.dataset / "manifest.json").read_text())
    collected = json.loads((args.dataset / "report.json").read_text())
    if not collected["full_dataset_complete"] or collected["smoke"] or manifest["roles"] != {k: list(v) for k, v in ROLES.items()}:
        raise ValueError("Incomplete or unexpected dataset")
    for name, digest in collected["output_hashes"].items():
        if sha(args.dataset / name) != digest:
            raise ValueError("Dataset changed")
    for name, digest in manifest["input_hashes"].items():
        if sha(Path(name)) != digest:
            raise ValueError("Original collection inputs changed")
    with zipfile.ZipFile(args.dataset / "source_snapshot.zip") as z:
        for name, digest in manifest["source_hashes"].items():
            if hashlib.sha256(z.read(name)).hexdigest() != digest:
                raise ValueError("Collection source archive mismatch")
    feature_source = ROOT / "research/policies/action_rank_policy.py"
    if sha(feature_source) != manifest["source_hashes"].get("research/policies/action_rank_policy.py"):
        raise ValueError("Observable features changed since collection")
    sources = [Path(__file__), PROTOCOL, feature_source,
               ROOT / "research/datasets/collect_action_rank_dataset.py", ROOT / "research/scenarios/scenario_schema.py",
               ROOT / "research/training/train_policy.py"]
    inputs = [args.dataset / n for n in ("manifest.json", "report.json", "source_snapshot.zip",
                                        "fit.jsonl", "calibration.jsonl", "probe.jsonl")]
    hashes = {str(p.resolve()): sha(p) for p in inputs}
    args.output.mkdir(parents=True, exist_ok=False)
    write(args.output / "manifest.json", dict(input_hashes=hashes, parents=manifest["parents"],
          source_hashes={str(p.relative_to(ROOT)): sha(p) for p in sources}, primary="calibrated"))
    with zipfile.ZipFile(args.output / "source_snapshot.zip", "x") as z:
        for p in sources:
            z.write(p, str(p.relative_to(ROOT)))
    fit = read_role(args.dataset, "fit", manifest)
    models = {p: fit_point([r for r in fit if r["training_seed"] == p], p,
                          manifest["parents"][str(p)]["sha256"]) for p in PARENTS}
    for p, payload in models.items():
        write(args.output / f"point_{p}.json", payload)
    write(args.output / "frozen_points.json", {str(p): sha(args.output / f"point_{p}.json") for p in PARENTS})
    calibration = read_role(args.dataset, "calibration", manifest)
    models = {p: calibrate(payload, [r for r in calibration if r["training_seed"] == p])
              for p, payload in models.items()}
    for p, payload in models.items():
        write(args.output / f"calibrated_{p}.json", payload)
    frozen = {str(p): sha(args.output / f"calibrated_{p}.json") for p in PARENTS}
    write(args.output / "frozen_calibrated.json", frozen)
    probe = read_role(args.dataset, "probe", manifest)
    alternatives, decisions = [], []
    for p, payload in models.items():
        a, d = probe_predictions(payload, [r for r in probe if r["training_seed"] == p])
        alternatives.extend(a)
        decisions.extend(d)
    for name, records in (("alternatives.jsonl", alternatives), ("decisions.jsonl", decisions)):
        with (args.output / name).open("x") as stream:
            for row in records:
                stream.write(json.dumps(row, allow_nan=False) + "\n")
    report = summarize(alternatives, decisions)
    all_rows = fit + calibration + probe
    branches = [b for r in all_rows for e in r["events"] for b in e.get("all_action_branches", [])]
    sample_count = sum(r["signal_samples"] for r in all_rows) + sum(b["outcome"]["signal_samples"] for b in branches)
    if (len(all_rows) != collected["planned_runs"] or len(branches) != collected["branches"]
            or sample_count != collected["labelled_source_and_branch_signal_samples"]):
        raise ValueError("Collection aggregate mismatch")
    if any(sha(Path(p)) != digest for p, digest in hashes.items()):
        raise ValueError("Input changed during calibration")
    if any(sha(args.output / f"calibrated_{p}.json") != frozen[str(p)] for p in PARENTS):
        raise ValueError("Calibrated model changed during probe")
    report["verified_collection"] = dict(source_runs=len(all_rows), branches=len(branches), signal_samples=sample_count)
    report["normalized_margins"] = {str(p): m["normalized_margin"] for p, m in models.items()}
    write(args.output / "report.json", report)
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
