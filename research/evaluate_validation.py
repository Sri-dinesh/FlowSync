#!/usr/bin/env python3
"""Compare a candidate on validation scenarios without touching the final tests."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import zipfile
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import torch

from research.train_policy import load_split, file_hash, VALIDATION_FAULTS, VALIDATION_SEEDS
from research.experiments.engine import ExperimentRunner
from research.experiments.shielded_controller import ShieldedController
from research.noise.fault_injector import PerceptionFaultInjector
from server.app.controllers import get_controller


def supervisor_variants(calibration):
    """Matched 2x2 intervention design plus policy/teacher reference controls."""
    common = {"calibration_path": str(calibration)} if calibration else {}
    variants = {"d3qn": ("d3qn", {}), "max_pressure": ("max_pressure", {})}
    for label, shield, fallback in (("uq_disabled", False, False),
                                    ("uq_shield_only", True, False),
                                    ("uq_fallback_only", False, True),
                                    ("uq_full", True, True)):
        variants[label] = ("flowsync_uq", {**common, "enable_shield": shield,
                                          "enable_fallback": fallback})
    return variants


def benefit_gate_variants(calibration, gate):
    if not calibration:
        raise ValueError("Benefit-gate comparison requires the recorded calibration")
    common = {"calibration_path": str(calibration), "enable_shield": True}
    return {"uq_shield_only": ("flowsync_uq", {**common, "enable_fallback": False}),
            "uq_full": ("flowsync_uq", common),
            "uq_gated": ("flowsync_uq", {**common, "benefit_gate_path": str(gate)})}


def policy_pair_variants(parent):
    if parent is None:
        raise ValueError("Paired validation requires a frozen parent checkpoint")
    common = {"enable_shield": True, "enable_fallback": False}
    return {"candidate": ("flowsync_uq", dict(common)),
            "parent": ("flowsync_uq", {**common, "checkpoint_path": str(parent)})}


def baseline_variants():
    return {**{name: (name, {}) for name in ("fixed", "actuated", "greedy", "max_pressure")},
            "max_pressure_shield": ("max_pressure", {"apply_shield": True})}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--checkpoint", type=Path)
    p.add_argument("--parent-checkpoint", type=Path)
    p.add_argument("--policy-pair", action="store_true", help="Candidate and frozen parent under identical shields; no fallback")
    p.add_argument("--baseline-panel", action="store_true", help="Five classical references, including matched Max-Pressure + shield")
    p.add_argument("--uq-calibration", type=Path)
    p.add_argument("--benefit-gate", type=Path,
                   help="Fixed gate comparison against original UQ and shield-only; no tuning")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--validation-seeds", type=int, nargs="+", default=list(VALIDATION_SEEDS))
    p.add_argument("--supervisor-ablation", action="store_true",
                   help="Matched shield/fallback factorial on validation only; no threshold search")
    args = p.parse_args()
    if len(set(args.validation_seeds)) != len(args.validation_seeds) or min(args.validation_seeds) < 0:
        p.error("Validation seeds must be nonnegative and unique")
    if args.benefit_gate and (not args.uq_calibration or args.supervisor_ablation):
        p.error("Benefit gate requires calibration and cannot be combined with supervisor ablation")
    if sum(bool(x) for x in (args.benefit_gate, args.supervisor_ablation, args.policy_pair, args.baseline_panel)) > 1:
        p.error("Choose only one comparison panel")
    if not args.baseline_panel and not args.checkpoint:
        p.error("A trained checkpoint is required except for the baseline-only panel")
    if args.policy_pair and not args.parent_checkpoint:
        p.error("Policy-pair comparison requires a parent checkpoint")
    if args.parent_checkpoint and not args.policy_pair:
        p.error("Parent checkpoint is only used by the policy-pair panel")
    if (args.baseline_panel or args.policy_pair) and args.uq_calibration:
        p.error("These panels do not use uncertainty calibration")
    if args.baseline_panel and args.checkpoint:
        p.error("Baseline-only panel does not use a checkpoint")
    args.output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    variants = {"fixed": ("fixed", {}), "actuated": ("actuated", {}), "greedy": ("greedy", {}),
                "max_pressure": ("max_pressure", {}), "d3qn": ("d3qn", {}),
                "uq_heuristic": ("flowsync_uq", {})}
    if args.uq_calibration:
        variants.update(uq_fitted=("flowsync_uq", {"calibration_path": str(args.uq_calibration)}),
                        uq_fitted_no_shield=("flowsync_uq", {"calibration_path": str(args.uq_calibration), "enable_shield": False}))
    if args.supervisor_ablation:
        variants = supervisor_variants(args.uq_calibration)
    if args.benefit_gate:
        variants = benefit_gate_variants(args.uq_calibration, args.benefit_gate)
    if args.policy_pair:
        variants = policy_pair_variants(args.parent_checkpoint)
    if args.baseline_panel:
        variants = baseline_variants()
    scenarios = load_split("validation")
    checkpoint_hashes = {label: file_hash(options.get("checkpoint_path", args.checkpoint))
                         for label, (name, options) in variants.items() if name in ("d3qn", "flowsync_uq")}
    configuration = {"checkpoint": str(args.checkpoint.resolve()) if args.checkpoint else None,
                     "checkpoint_sha256": file_hash(args.checkpoint) if args.checkpoint else None,
                     "variant_checkpoint_hashes": checkpoint_hashes,
                     "calibration_sha256": file_hash(args.uq_calibration) if args.uq_calibration else None,
                     "benefit_gate_sha256": file_hash(args.benefit_gate) if args.benefit_gate else None,
                     "seeds": args.validation_seeds, "faults": [asdict(f) for f in VALIDATION_FAULTS],
                     "split": "validation", "variants": variants,
                     "scenario_hashes": {sc.scenario_id: sc.compute_hash() for sc in scenarios},
                     "planned_runs": len(scenarios)*len(args.validation_seeds)*len(VALIDATION_FAULTS)*len(variants),
                     "source_hashes": {str(path.relative_to(ROOT)): file_hash(path)
                                       for base in (ROOT/"research", ROOT/"server/app") for path in sorted(base.rglob("*.py"))}}
    (args.output / "configuration.json").write_text(json.dumps(configuration, indent=2))
    with zipfile.ZipFile(args.output/"source_snapshot.zip", "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in configuration["source_hashes"]:
            archive.write(ROOT/source, source)
        for scenario in sorted((ROOT/"research/scenarios/validation").glob("*.yaml")):
            archive.write(scenario, str(scenario.relative_to(ROOT)))
        if args.benefit_gate:
            archive.write(args.benefit_gate, "artifacts/benefit_gate.json")
        if args.uq_calibration:
            archive.write(args.uq_calibration, "artifacts/calibration.json")
    runner, rows = ExperimentRunner(), []
    for sc in scenarios:
        for seed in args.validation_seeds:
            for fault in VALIDATION_FAULTS:
                for label, (name, options) in variants.items():
                    kwargs = dict(options)
                    if name in ("d3qn", "flowsync_uq"):
                        kwargs.setdefault("checkpoint_path", str(args.checkpoint))
                    shield = kwargs.pop("apply_shield", False)
                    controller = get_controller(name, **kwargs)
                    if shield:
                        controller = ShieldedController(controller)
                    result = runner.run(controller, sc, seed, record_trajectory=False,
                                        fault_injector=PerceptionFaultInjector(fault, seed=seed+90000))
                    result.save_bundle(args.output / "bundles" / label / fault.name)
                    row = {"scenario": sc.scenario_id, "seed": seed, "fault": fault.name, "controller": label,
                           "scenario_hash": result.scenario_hash,
                           "delay": result.avg_delay, "p95": result.p95_delay, "throughput": result.total_vehicles_passed,
                           "fallback_steps": result.fallback_steps, "fallback_activations": result.fallback_activations,
                           "shield_interventions": result.shield_interventions, "starvations": result.starvation_count,
                           "checkpoint_hash": result.checkpoint_hash,
                           "calibration_hash": result.controller_diagnostics.get("uncertainty_calibration_hash"),
                           "benefit_gate_hash": result.controller_diagnostics.get("benefit_gate_hash"),
                           "gate_evaluations": result.controller_diagnostics.get("benefit_gate_evaluations", 0),
                           "gate_vetoes": result.controller_diagnostics.get("benefit_gate_vetoes", 0),
                           "safety_samples": result.safety_samples, "expected_safety_samples": sc.duration_steps,
                           "shield_override_reasons": result.controller_diagnostics.get("shield", {}).get("override_counts_by_reason", {}),
                           "signal_violations": result.executed_conflict_violations + result.executed_clearance_violations,
                           "arrivals_hash": result.arrival_trace_hash}
                    rows.append(row)
                    if row["scenario_hash"] != configuration["scenario_hashes"][sc.scenario_id]:
                        raise RuntimeError("Executed scenario differs from frozen configuration")
                    if name in ("d3qn", "flowsync_uq") and row["checkpoint_hash"] != checkpoint_hashes[label]:
                        raise RuntimeError("Executed checkpoint differs from frozen configuration")
                    if label == "uq_gated" and (row["benefit_gate_hash"] != configuration["benefit_gate_sha256"]
                            or row["calibration_hash"] != configuration["calibration_sha256"]):
                        raise RuntimeError("Executed gate/calibration differs from frozen configuration")
                    with (args.output / "runs.jsonl").open("a") as stream:
                        stream.write(json.dumps(row) + "\n")
        print(f"Completed {sc.scenario_id}", flush=True)
    paired_hashes = {}
    if len(rows) != configuration["planned_runs"] or len({(r["scenario"], r["seed"], r["fault"], r["controller"])
                                                         for r in rows}) != len(rows):
        raise RuntimeError("Incomplete or duplicated validation cells")
    for row in rows:
        paired_hashes.setdefault((row["scenario"], row["seed"]), set()).add(row["arrivals_hash"])
    if any(len(hashes) != 1 for hashes in paired_hashes.values()):
        raise RuntimeError("Traffic arrivals differ across paired controllers")
    if any(r["safety_samples"] != r["expected_safety_samples"] for r in rows):
        raise RuntimeError("Incomplete signal-audit coverage")
    if any(not np.isfinite([r["delay"], r["p95"], r["throughput"]]).all() for r in rows):
        raise RuntimeError("Nonfinite traffic metrics")
    summary = {}
    for label in variants:
        subset = [r for r in rows if r["controller"] == label]
        summary[label] = {"mean_delay": float(np.mean([r["delay"] for r in subset])),
                          "mean_p95": float(np.mean([r["p95"] for r in subset])),
                          "runs": len(subset),
                          "mean_throughput": float(np.mean([r["throughput"] for r in subset])),
                          "starvations": sum(r["starvations"] for r in subset),
                          "shield_interventions": sum(r["shield_interventions"] for r in subset),
                          "fallback_steps": sum(r["fallback_steps"] for r in subset),
                          "fallback_activations": sum(r["fallback_activations"] for r in subset),
                          "gate_evaluations": sum(r["gate_evaluations"] for r in subset),
                          "gate_vetoes": sum(r["gate_vetoes"] for r in subset),
                          "safety_samples": sum(r["safety_samples"] for r in subset),
                          "signal_violations": sum(r["signal_violations"] for r in subset)}
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
