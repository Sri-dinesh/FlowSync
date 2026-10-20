#!/usr/bin/env python3
"""Fit synthetic observation-error risk on validation-only, seed-separated data.

This estimates a defined count-error event, NOT accident probability or the
benefit of fallback. A useful classifier need not be a useful control supervisor.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import rankdata

from research.train_policy import load_split, file_hash
from research.experiments.engine import ExperimentRunner
from research.noise.fault_injector import FaultProfile, PerceptionFaultInjector
from research.uncertainty.estimator import UncertaintyFeatures
from server.app.controllers.flowsync_uq import FlowSyncUQController

FEATURE_NAMES = list(UncertaintyFeatures().to_dict())
FAULTS = [FaultProfile(), FaultProfile(name="miss_15", miss_rate=.15),
          FaultProfile(name="miss_25", miss_rate=.25),
          FaultProfile(name="latency_300", latency_ms=300),
          FaultProfile(name="mixed", miss_rate=.2, latency_ms=200, false_positive_lambda=.1)]


def binary_metrics(y, p, threshold=.5):
    y, p = np.asarray(y, dtype=int), np.asarray(p, dtype=float)
    positive, negative = y == 1, y == 0
    pred = p >= threshold
    auc = None
    if positive.any() and negative.any():
        n = positive.sum()
        auc = float((rankdata(p)[positive].sum() - n * (n + 1) / 2) / (n * negative.sum()))
    ece = 0.0
    bins = np.minimum((p * 10).astype(int), 9)
    for b in range(10):
        mask = bins == b
        if mask.any():
            ece += float(mask.mean() * abs(p[mask].mean() - y[mask].mean()))
    return {"n": len(y), "positive_fraction": float(y.mean()), "roc_auc": auc,
            "brier": float(np.mean((p-y)**2)), "ece": ece,
            "recall": float(pred[positive].mean()) if positive.any() else None,
            "false_positive_rate": float(pred[negative].mean()) if negative.any() else None}


def fit_calibration(x, y):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if x.ndim != 2 or x.shape[1] != 7 or len(x) != len(y) or len(np.unique(y)) != 2:
        raise ValueError("Calibration needs seven features and both error classes")
    mean, scale = x.mean(0), np.maximum(x.std(0), .001)
    z = (x - mean) / scale
    def objective(params):
        logits = z @ params[:7] + params[7]
        loss = np.mean(np.logaddexp(0, logits) - y * logits) + .005 * np.sum(params[:7] ** 2)
        residual = expit(logits) - y
        gradient = np.r_[z.T @ residual / len(y) + .01 * params[:7], residual.mean()]
        return loss, gradient
    fit = minimize(objective, np.zeros(8), jac=True, method="L-BFGS-B",
                   bounds=[(0, None)] * 7 + [(None, None)])
    if not fit.success:
        raise RuntimeError(f"Calibration optimization failed: {fit.message}")
    return {"version": "synthetic_error_logistic_v1", "feature_names": FEATURE_NAMES,
            "mean": mean.tolist(), "scale": scale.tolist(),
            "coefficients": fit.x[:7].tolist(), "intercept": float(fit.x[7])}


def predict(model, x):
    z = (np.asarray(x) - model["mean"]) / model["scale"]
    return expit(z @ np.asarray(model["coefficients"]) + model["intercept"])


def select_threshold(y, probabilities, max_false_positive_rate=.1):
    candidates = np.unique(np.r_[.01, probabilities, 1.0])
    eligible = []
    for threshold in candidates:
        m = binary_metrics(y, probabilities, threshold)
        if m["false_positive_rate"] is not None and m["false_positive_rate"] <= max_false_positive_rate:
            eligible.append((m["recall"] or 0, -m["false_positive_rate"], float(threshold)))
    if not eligible:
        raise ValueError("No valid threshold for requested false-alarm constraint")
    return max(eligible)[2]


def collect(checkpoint, output):
    rows = []
    runner = ExperimentRunner()
    for split, seed in (("fit", 31001), ("threshold", 31002), ("audit", 31003)):
        for scenario in load_split("validation"):
            for fault in FAULTS:
                ctrl = FlowSyncUQController(checkpoint_path=str(checkpoint), enable_fallback=False, enable_shield=False)
                result = runner.run(ctrl, scenario, seed, record_trajectory=True,
                                    fault_injector=PerceptionFaultInjector(fault, seed=seed+90000))
                result.save_bundle(output / "bundles" / split / fault.name)
                for frame in result.trajectory:
                    clean = np.rint(15 * np.arctanh(np.clip(frame["clean_observation"][:12], 0, .999999)))
                    noisy = np.rint(15 * np.arctanh(np.clip(frame["policy_observation"][:12], 0, .999999)))
                    error = float(np.abs(clean-noisy).sum())
                    rows.append({"split": split, "seed": seed, "scenario": scenario.scenario_id,
                                 "fault": fault.name, "step": frame["step"],
                                 "features": [frame["uncertainty_features"][f] for f in FEATURE_NAMES],
                                 "count_error_l1": error, "high_error": int(error >= 3),
                                 "heuristic_score": frame["uncertainty_score"]})
        print(f"Collected {split} calibration data", flush=True)
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    rows = collect(args.checkpoint, args.output)
    (args.output / "samples.json").write_text(json.dumps(rows))
    def xy(split):
        subset = [r for r in rows if r["split"] == split]
        return np.asarray([r["features"] for r in subset]), np.asarray([r["high_error"] for r in subset])
    model = fit_calibration(*xy("fit"))
    x, y = xy("threshold")
    threshold = select_threshold(y, predict(model, x))
    model.update(threshold_high=threshold, threshold_low=threshold*.6,
                 target="sum absolute synthetic count error >= 3 vehicles across 12 movements",
                 fit_seed=31001, threshold_seed=31002, audit_seed=31003,
                 checkpoint_sha256=file_hash(args.checkpoint),
                 scenario_hashes={s.scenario_id: s.compute_hash() for s in load_split("validation")},
                 fault_profiles=[asdict(f) for f in FAULTS],
                 source_hashes={str(path.relative_to(ROOT)): file_hash(path)
                                for base in (ROOT/"research", ROOT/"server/app") for path in sorted(base.rglob("*.py"))})
    (args.output / "calibration.json").write_text(json.dumps(model, indent=2))
    report = {"publication_ready": False, "threshold_high": threshold,
              "limitations": ["Synthetic count error, not camera confidence or safety probability",
                              "Samples within each trajectory are temporally correlated",
                              "One audit traffic seed; no independent policy-training replication",
                              "Classifier accuracy does not establish fallback utility"], "splits": {}}
    for split in ("fit", "threshold", "audit"):
        x, y = xy(split)
        subset = [r for r in rows if r["split"] == split]
        report["splits"][split] = {"fitted": binary_metrics(y, predict(model, x), threshold),
                                  "heuristic": binary_metrics(y, [r["heuristic_score"] for r in subset], .45)}
    (args.output / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
