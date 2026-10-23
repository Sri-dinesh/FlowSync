#!/usr/bin/env python3
"""Fit one fixed-regularization fallback gate, using training-split events only."""
import argparse
import json
from itertools import product
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit

from research.training.train_policy import file_hash
from research.uncertainty.benefit_gate import FEATURE_NAMES


def samples(manifest, rows):
    if manifest["arguments"]["split"] != "train" or any(r.get("split") != "train" for r in rows):
        raise ValueError("Benefit gate fitting requires training-only data")
    if manifest.get("feature_names") != FEATURE_NAMES or len(rows) != manifest["planned_runs"]:
        raise ValueError("Incomplete or incompatible training audit")
    expected = set(product(manifest["scenario_hashes"], manifest["arguments"]["seeds"],
                           [f["name"] for f in manifest["faults"]],
                           [c["sha256"] for c in manifest["choices"]]))
    actual = [(r["scenario"], r["seed"], r["fault"]["name"], r["checkpoint_hash"]) for r in rows]
    if len(expected) != len(rows) or set(actual) != expected:
        raise ValueError("Missing, duplicate or unexpected training cells")
    x, y = [], []
    for row in rows:
        if row["scenario_hash"] != manifest["scenario_hashes"][row["scenario"]]:
            raise ValueError("Training scenario provenance mismatch")
        for event in row["events"]:
            if event["kind"] != "fallback_entry" or event["stale_observation_failover"] or "intervention_kept" not in event:
                continue
            if event["horizon_steps"] != 200:
                raise ValueError("Gate target requires the frozen 20-second horizon")
            kept, omitted = event["intervention_kept"], event["intervention_omitted"]
            if kept["arrival_trace_hash"] != omitted["arrival_trace_hash"]:
                raise ValueError("Unpaired counterfactual labels")
            for branch in (kept, omitted):
                metrics = [branch[k] for k in ("incremental_delay_vehicle_seconds", "upstream_max_wait_s",
                                               "signal_samples", "signal_violations")]
                if not np.isfinite(metrics).all() or min(metrics) < 0 or branch["signal_samples"] != 200:
                    raise ValueError("Invalid or incomplete counterfactual measurements")
            x.append(event["observable_features"])
            y.append(int(omitted["incremental_delay_vehicle_seconds"] - kept["incremental_delay_vehicle_seconds"] > 1e-6
                         and kept["upstream_max_wait_s"] <= omitted["upstream_max_wait_s"] + 1e-6
                         and kept["signal_violations"] == 0))
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if x.ndim != 2 or x.shape[1] != len(FEATURE_NAMES) or not np.isfinite(x).all():
        raise ValueError("Missing/invalid observable training features")
    if min(np.sum(y == 0), np.sum(y == 1)) < 10:
        raise ValueError("Need at least ten observed examples of each outcome; do not manufacture a gate")
    return x, y


def fit(x, y):
    mean, scale = x.mean(0), np.maximum(x.std(0), .001)
    z = (x-mean)/scale
    def loss(parameters):
        logits = z @ parameters[:-1] + parameters[-1]
        residual = expit(logits) - y
        return (np.mean(np.logaddexp(0, logits)-y*logits) + .1*np.sum(parameters[:-1]**2),
                np.r_[z.T @ residual/len(y)+.2*parameters[:-1], residual.mean()])
    solution = minimize(loss, np.zeros(len(FEATURE_NAMES)+1), jac=True, method="L-BFGS-B")
    if not solution.success or not np.isfinite(solution.x).all():
        raise RuntimeError("Benefit gate optimization failed")
    return {"version": "fallback_benefit_logistic_v1", "feature_names": FEATURE_NAMES,
            "mean": mean.tolist(), "scale": scale.tolist(), "coefficients": solution.x[:-1].tolist(),
            "intercept": float(solution.x[-1]), "threshold": .5,
            "target": "20s total waiting reduction AND no increased endpoint upstream maximum accumulated wait",
            "training_samples": len(y), "training_positive_fraction": float(y.mean()),
            "l2_penalty": .1, "publication_ready": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("training_audit", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    manifest = json.loads((args.training_audit/"manifest.json").read_text())
    rows = [json.loads(line) for line in (args.training_audit/"runs.jsonl").read_text().splitlines()]
    model = fit(*samples(manifest, rows))
    model.update(calibration_sha256=manifest["calibration_sha256"],
                 checkpoint_hashes=[c["sha256"] for c in manifest["choices"]],
                 training_audit_manifest_sha256=file_hash(args.training_audit/"manifest.json"),
                 training_audit_rows_sha256=file_hash(args.training_audit/"runs.jsonl"),
                 fitter_sha256=file_hash(Path(__file__)))
    with args.output.open("x") as stream:
        json.dump(model, stream, indent=2)
    print(json.dumps(model, indent=2))


if __name__ == "__main__":
    main()
