#!/usr/bin/env python3
"""FlowSync-UQ: reproducible backend-only evaluation using the existing ExperimentRunner.

Run from the project root (no frontend/web server needed):
    python research/evaluation/run_headless_evaluation.py --suite smoke --seeds 2 --checkpoint PATH.pt
    python research/evaluation/run_headless_evaluation.py --suite full --seeds 20 --checkpoint PATH.pt

Evidence caveats: checkpoint selection, simulation timestep, CRN arrival schedules,
shared physical FSM, and executed signal safety must be verified against the
underlying backend code before calling the results publication-ready.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if not (ROOT / "research" / "scenarios" / "loader.py").is_file():
    raise SystemExit("Place this script at <FlowSync>/research/evaluation/run_headless_evaluation.py")
sys.path.insert(0, str(ROOT))

from research.experiments.engine import ExperimentRunner  # noqa: E402
from research.noise.fault_injector import FaultProfile, PerceptionFaultInjector  # noqa: E402
from research.scenarios.loader import load_scenario  # noqa: E402
from server.app.controllers import get_controller  # noqa: E402
from server.app.controllers.flowsync_uq import FlowSyncUQController  # noqa: E402
from server.app.simulation.benchmark_harness import seed_everything  # noqa: E402

CONTROLLERS = (
    "fixed", "actuated", "greedy", "max_pressure", "dqn", "d3qn", "flowsync_uq"
)
TEST_SCENARIOS = (
    "test_clean_balanced_01", "test_near_gridlock_01",
    "test_left_turn_surge_01", "test_sudden_burst_01",
    "test_heldout_ood_01", "test_demand_reversal_01",
    "test_incident_reduction_01",
)
NOISE_NAMES = (
    "clean", "miss_10", "miss_20", "miss_30", "miss_40",
    "burst_occl", "latency_300ms", "latency_1000ms", "combined_severe",
)
NOISE_CONTROLLERS = (
    "fixed", "actuated", "max_pressure", "dqn", "d3qn", "flowsync_uq"
)
ABLATIONS = (
    "full_uq", "blind_d3qn", "without_shield", "without_fallback", "fixed_fallback",
)
FIELDS = (
    "suite", "scenario", "condition", "seed", "controller", "status",
    "avg_delay_s", "p95_vehicle_delay_s", "max_queue_vehicles",
    "throughput_veh_per_hour", "vehicles_passed", "starvations",
    "watchdog_overrides", "executed_conflict_violations", "elapsed_wall_s", "error",
    "executed_clearance_violations", "safety_samples", "fallback_steps",
    "fallback_activations", "shield_interventions", "observation_mae",
    "checkpoint_hash", "checkpoint_path", "checkpoint_episode", "arrival_trace_hash",
    "realized_miss_rate", "incident_active_steps",
)


def noise_profile(name: str) -> Any:
    """Return a fresh profile each time to prevent cross-controller state sharing."""
    args = {
        "miss_10": dict(miss_rate=0.10),
        "miss_20": dict(miss_rate=0.20),
        "miss_30": dict(miss_rate=0.30),
        "miss_40": dict(miss_rate=0.40),
        "burst_occl": dict(burst_miss_prob=0.08, burst_miss_duration=30),
        "latency_300ms": dict(latency_ms=300),
        "latency_1000ms": dict(latency_ms=1000),
        "combined_severe": dict(miss_rate=0.20, latency_ms=200,
                                false_positive_lambda=0.15, jitter_std=0.03),
        "ablation_faults": dict(miss_rate=0.25, latency_ms=150),
    }
    if name == "clean":
        return None
    return FaultProfile(name=name, **args[name])


def make_controller(name: str, checkpoint: str | None = None,
                    dqn_checkpoint: str | None = None,
                    calibration_path: str | None = None) -> Any:
    # Rebuild for EVERY run; recurrent/supervisor/FSM state must not leak across seeds.
    uq_options = {"calibration_path": calibration_path} if calibration_path else {}
    if name == "full_uq":
        return FlowSyncUQController(checkpoint_path=checkpoint, enable_shield=True, uncertainty_threshold=0.45,
                                    fallback_controller_name="max_pressure", **uq_options)
    if name == "blind_d3qn":
        return get_controller("d3qn", checkpoint_path=checkpoint)
    if name == "without_shield":
        return FlowSyncUQController(checkpoint_path=checkpoint, enable_shield=False, uncertainty_threshold=0.45,
                                    fallback_controller_name="max_pressure", **uq_options)
    if name == "without_fallback":
        return FlowSyncUQController(checkpoint_path=checkpoint, enable_shield=True, enable_fallback=False,
                                    fallback_controller_name="max_pressure", **uq_options)
    if name == "fixed_fallback":
        return FlowSyncUQController(checkpoint_path=checkpoint, enable_shield=True, uncertainty_threshold=0.45,
                                    fallback_controller_name="fixed", **uq_options)
    if name in ("d3qn", "flowsync_uq"):
        return get_controller(name, checkpoint_path=checkpoint, **(uq_options if name == "flowsync_uq" else {}))
    if name == "dqn":
        return get_controller(name, checkpoint_path=dqn_checkpoint)
    return get_controller(name)


def get_number(result: Any, name: str, *, required: bool = True) -> float | None:
    value = getattr(result, name, None)
    if value is None:
        if required:
            raise ValueError(f"ExperimentResult lacks required metric: {name}")
        return None
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"Metric {name} is nonfinite: {value}")
    return value


def manifest_seeds(path: Path, count: int) -> list[int]:
    if not path.is_file():
        raise FileNotFoundError(f"Frozen seed manifest not found: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    vals = manifest.get("seeds")
    if not isinstance(vals, list) or len(vals) < count:
        raise ValueError(f"Seed manifest must contain at least {count} entries")
    values = [int(s) for s in vals[:count]]
    if len(set(values)) != len(values):
        raise ValueError("Seed manifest contains duplicate seeds")
    return values


def git_info() -> dict[str, Any]:
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                    capture_output=True, text=True, check=True).stdout.strip())
        return {"commit": sha, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"commit": None, "dirty": None}


def source_digests() -> dict[str, str]:
    """Record source/config fingerprints, including scenario definitions."""
    paths = [ROOT / "research" / "evaluation" / "run_headless_evaluation.py"]
    for base, ext in ((ROOT / "server" / "app", "*.py"),
                      (ROOT / "research", "*.py"),
                      (ROOT / "research" / "scenarios", "*.yaml"),
                      (ROOT / "research" / "manifests", "*.json")):
        if base.exists():
            paths.extend(base.rglob(ext))
    # The exact checkpoint IN USE cannot be established from the supplied code.
    # Hash the candidate weights to at least detect changed artifact contents.
    model_dir = ROOT / "server" / "models"
    if model_dir.exists():
        paths.extend(model_dir.rglob("*.pt"))
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(set(paths)) if p.is_file()}


def jobs(suite: str, seeds: list[int]):
    if suite == "smoke":
        for seed in seeds:
            for c in ("fixed", "d3qn", "flowsync_uq"):
                yield ("clean", "test_clean_balanced_01", "clean", seed, c)
            for c in ("d3qn", "flowsync_uq"):
                yield ("robustness", "test_clean_balanced_01", "miss_30", seed, c)
        return
    for sc in TEST_SCENARIOS:
        for seed in seeds:
            for c in CONTROLLERS:
                yield ("clean", sc, "clean", seed, c)
    for cond in NOISE_NAMES:
        for seed in seeds:
            for c in NOISE_CONTROLLERS:
                yield ("robustness", "test_clean_balanced_01", cond, seed, c)
    # Missing counts alone may not cross the supervisor threshold. The stale
    # camera condition independently exercises the fallback code path.
    for cond in ("ablation_faults", "latency_1000ms"):
        for seed in seeds:
            for c in ABLATIONS:
                yield ("ablation", "test_clean_balanced_01", cond, seed, c)


def evaluate_one(job: tuple, step_seconds: float,
                 record_trajectory: bool, checkpoint: str | None = None,
                 dqn_checkpoint: str | None = None, bundle_dir: Path | None = None,
                 calibration_path: str | None = None) -> dict[str, Any]:
    suite, sc_name, cond, seed, ctrl_name = job
    row = dict.fromkeys(FIELDS, "")
    row.update(suite=suite, scenario=sc_name, condition=cond,
               seed=seed, controller=ctrl_name, status="failed")
    start = time.perf_counter()
    try:
        runner = ExperimentRunner()  # New runner and controller for each independent run.
        seed_everything(int(seed))
        controller = make_controller(ctrl_name, checkpoint, dqn_checkpoint, calibration_path)
        scenario = load_scenario(sc_name)  # Fresh scenario; never reuse mutable state.
        injector = None
        if cond != "clean":
            injector = PerceptionFaultInjector(noise_profile(cond))
            # Same starting RNG seed for each controller with this traffic seed+fault.
            # Equal RNG seeds DO NOT by themselves prove identical fault timelines.
            injector.reset_seed(int(seed) + 90_000)
        result = runner.run(controller, scenario, seed=int(seed),
                            record_trajectory=record_trajectory,
                            fault_injector=injector)
        if bundle_dir is not None:
            result.save_bundle(bundle_dir / suite / cond / ctrl_name)
        delay = get_number(result, "avg_delay")
        p95 = get_number(result, "p95_delay")
        queue = get_number(result, "max_queue")
        passed = get_number(result, "total_vehicles_passed")
        starvation = get_number(result, "starvation_count")
        overrides = get_number(result, "watchdog_override_count")
        duration_steps = float(getattr(scenario, "duration_steps"))
        duration_s = duration_steps * step_seconds
        if duration_s <= 0:
            raise ValueError("Scenario duration must be positive")
        # Only use explicit safety measurements; never fabricate zero violations.
        executed = get_number(result, "executed_conflict_violations", required=False)
        row.update(status="ok", avg_delay_s=delay, p95_vehicle_delay_s=p95,
                   max_queue_vehicles=queue,
                   throughput_veh_per_hour=passed * 3600.0 / duration_s,
                   vehicles_passed=passed, starvations=starvation,
                   watchdog_overrides=overrides,
                   executed_conflict_violations="" if executed is None else executed)
        for key in ("executed_clearance_violations", "safety_samples", "fallback_steps",
                    "fallback_activations", "shield_interventions", "observation_mae",
                    "checkpoint_hash", "arrival_trace_hash"):
            row[key] = getattr(result, key)
        diag = result.controller_diagnostics
        row["checkpoint_path"] = diag.get("checkpoint_path") or ""
        row["checkpoint_episode"] = (diag.get("checkpoint_metadata") or {}).get("episode", "")
        row["realized_miss_rate"] = result.fault_diagnostics.get("realized_miss_rate", 0.0)
        row["incident_active_steps"] = result.scenario_diagnostics["incident_active_steps"]
    except Exception as exc:
        row["error"] = f"{type(exc).__name__}: {exc}"
    row["elapsed_wall_s"] = round(time.perf_counter() - start, 4)
    return row


def ci_mean(values: np.ndarray, bootstrap: int, rng: np.random.Generator) -> list[float] | None:
    if len(values) < 2:
        return None
    samples = rng.choice(values, size=(bootstrap, len(values)), replace=True).mean(axis=1)
    return [float(x) for x in np.quantile(samples, [0.025, 0.975])]


def fnum(row: dict[str, Any], key: str) -> float | None:
    try:
        x = float(row[key])
        return x if np.isfinite(x) else None
    except (TypeError, KeyError, ValueError):
        return None


def analyze(rows: list[dict[str, Any]], boots: int, min_inference: int):
    rng = np.random.default_rng(20261008)
    good = [r for r in rows if r["status"] == "ok"]
    groups = defaultdict(list)
    for r in good:
        groups[(r["suite"], r["scenario"], r["condition"], r["controller"])].append(r)
    summaries = []
    for (suite, scenario, condition, controller), items in sorted(groups.items()):
        arr = np.array([float(r["avg_delay_s"]) for r in items], dtype=float)
        p95_arr = np.array([float(r["p95_vehicle_delay_s"]) for r in items])
        executed_values = [fnum(r, "executed_conflict_violations") for r in items]
        summary = {
            "suite": suite, "scenario": scenario, "condition": condition,
            "controller": controller, "n_runs": len(items),
            "mean_delay_s": float(arr.mean()),
            "sd_delay_s": float(arr.std(ddof=1)) if len(arr) > 1 else None,
            "mean_delay_ci95_s": ci_mean(arr, boots, rng),
            "mean_within_run_p95_vehicle_delay_s": float(p95_arr.mean()),
            "mean_max_queue": float(np.mean([float(r["max_queue_vehicles"]) for r in items])),
            "mean_throughput_veh_h": float(np.mean([float(r["throughput_veh_per_hour"]) for r in items])),
            "total_starvations": int(sum(float(r["starvations"]) for r in items)),
            "total_watchdog_overrides": int(sum(float(r["watchdog_overrides"]) for r in items)),
            "executed_safety_violations": (int(sum(executed_values))
                if all(v is not None for v in executed_values) else None),
        }
        summaries.append(summary)
    by_sc_cond = defaultdict(lambda: defaultdict(dict))
    for r in good:
        by_sc_cond[(r["suite"], r["scenario"], r["condition"])][r["controller"]][int(r["seed"])] = float(r["avg_delay_s"])
    comparisons = []
    for (suite, scenario, condition), controller_map in sorted(by_sc_cond.items()):
        proposed_name = "full_uq" if suite == "ablation" else "flowsync_uq"
        if proposed_name not in controller_map:
            continue
        tests = []
        for baseline in sorted(controller_map):
            if baseline == proposed_name:
                continue
            common = sorted(set(controller_map[baseline]) & set(controller_map[proposed_name]))
            if not common:
                continue
            a = np.array([controller_map[baseline][s] for s in common])
            b = np.array([controller_map[proposed_name][s] for s in common])
            diffs = a - b  # Positive => FlowSync-UQ reduces delay.
            record = {
                "suite": suite, "scenario": scenario, "condition": condition,
                "baseline": baseline, "proposed": proposed_name, "n_paired_seeds": len(common),
                "mean_baseline_delay_s": float(a.mean()),
                "mean_proposed_delay_s": float(b.mean()),
                "mean_delay_saved_s": float(diffs.mean()),
                "relative_improvement_pct": float(100 * diffs.mean() / a.mean()) if a.mean() != 0 else None,
                "paired_bootstrap_ci95_saved_s": ci_mean(diffs, boots, rng),
                "cohens_dz": (float(diffs.mean() / diffs.std(ddof=1))
                              if len(diffs) > 1 and diffs.std(ddof=1) > 0 else None),
                "paired_t_p_raw": None, "wilcoxon_p_raw": None,
                "paired_t_p_holm": None, "significant_at_0_05": None,
            }
            if len(common) >= min_inference:
                try:
                    from scipy.stats import ttest_rel, wilcoxon
                    if not np.allclose(diffs, diffs[0]):
                        record["paired_t_p_raw"] = float(ttest_rel(a, b).pvalue)
                    elif diffs[0] != 0:
                        # Degenerate non-zero differences: t-test undefined; avoid reporting zero p.
                        pass
                    else:
                        record["paired_t_p_raw"] = 1.0
                    if np.any(diffs != 0):
                        record["wilcoxon_p_raw"] = float(wilcoxon(diffs).pvalue)
                    else:
                        record["wilcoxon_p_raw"] = 1.0
                except (ImportError, ValueError):
                    pass
            tests.append(record)
        # Holm-Bonferroni adjustment within each scenario/condition comparison family.
        pidx = sorted([(i, t["paired_t_p_raw"]) for i, t in enumerate(tests)
                       if t["paired_t_p_raw"] is not None], key=lambda v: v[1])
        prev = 0.0
        for rank, (idx, p) in enumerate(pidx):
            adjusted = min(1.0, max(prev, p * (len(pidx) - rank)))
            tests[idx]["paired_t_p_holm"] = float(adjusted)
            tests[idx]["significant_at_0_05"] = bool(adjusted < 0.05)
            prev = adjusted
        comparisons.extend(tests)
    return summaries, comparisons


def noise_degradation(rows: list[dict[str, Any]], boots: int) -> list[dict[str, Any]]:
    """Noise-vs-clean differences paired by identical scenario/controller/seed."""
    good = [r for r in rows if r["status"] == "ok" and r["suite"] == "robustness"]
    controls = defaultdict(dict)
    for r in good:
        controls[(r["scenario"], r["controller"], r["condition"])][int(r["seed"])] = float(r["avg_delay_s"])
    rng = np.random.default_rng(2106)
    results = []
    for (scenario, controller, condition), noisy in sorted(controls.items()):
        if condition == "clean":
            continue
        clean = controls.get((scenario, controller, "clean"), {})
        paired = sorted(set(noisy) & set(clean))
        if not paired:
            continue
        a = np.array([clean[s] for s in paired])
        b = np.array([noisy[s] for s in paired])
        delta = b - a  # Positive means degradation from perception faults.
        results.append({
            "scenario": scenario, "controller": controller, "noise_condition": condition,
            "n_paired_seeds": len(paired),
            "clean_mean_delay_s": float(a.mean()),
            "noisy_mean_delay_s": float(b.mean()),
            "mean_degradation_s": float(delta.mean()),
            "degradation_pct": float(100 * delta.mean() / a.mean()) if a.mean() != 0 else None,
            "paired_bootstrap_ci95_degradation_s": ci_mean(delta, boots, rng),
        })
    return results


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as out:
        fields = list(rows[0].keys())
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v) if isinstance(v, (dict, list)) else v
                             for k, v in row.items()})


def latex_table(path: Path, summaries: list[dict[str, Any]], suite: str,
                scenario: str, condition: str, caption: str) -> None:
    selected = [r for r in summaries if (r["suite"], r["scenario"], r["condition"])
                == (suite, scenario, condition)]
    if not selected:
        return
    lines = [r"\begin{table*}[t]", "\\caption{" + caption.replace("%", r"\%") + "}",
             r"\centering", r"\small", r"\begin{tabular}{lrrrr}", r"\toprule",
             r"Controller & $n$ & Mean delay (s) & Mean within-run P95 (s) & Throughput (veh/h) \\",
             r"\midrule"]
    for r in selected:
        ctrl = r["controller"].replace("_", r"\_")
        lines.append(f"{ctrl} & {r['n_runs']} & {r['mean_delay_s']:.2f} & "
                     f"{r['mean_within_run_p95_vehicle_delay_s']:.2f} & "
                     f"{r['mean_throughput_veh_h']:.1f} " + r"\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--suite", choices=("smoke", "full"), default="smoke")
    p.add_argument("--checkpoint", type=Path, required=True,
                   help="Explicit trained D3QN weights used by D3QN and EVERY UQ ablation")
    p.add_argument("--dqn-checkpoint", type=Path,
                   help="Separate PlainDQNNetwork weights; DQN is omitted if absent")
    p.add_argument("--controllers", help="Optional comma-separated subset, including ablation names")
    p.add_argument("--scenarios", help="Optional comma-separated subset of test scenario IDs")
    p.add_argument("--conditions", help="Optional comma-separated subset of noise conditions")
    p.add_argument("--seeds", type=int, default=None,
                   help="Number of frozen seeds; default: 2 smoke, 20 full")
    p.add_argument("--seed-manifest", type=Path,
                   default=Path("research/manifests/final_seed_manifest_v2.json"))
    p.add_argument("--output-dir", type=Path, default=None)
    p.add_argument("--sim-step-seconds", type=float, default=0.1,
                   help="Confirm against backend engine before publication (original runner used 0.1)")
    p.add_argument("--bootstrap", type=int, default=5000)
    p.add_argument("--min-seeds-for-inference", type=int, default=10)
    p.add_argument("--record-trajectories", action="store_true")
    p.add_argument("--uq-calibration", type=Path, help="Validation-fitted uncertainty artifact (optional)")
    p.add_argument("--resume", action="store_true", help="Continue ONLY identical recorded configuration")
    p.add_argument("--continue-on-error", action="store_true")
    args = p.parse_args()
    nseed = args.seeds if args.seeds is not None else (2 if args.suite == "smoke" else 20)
    if nseed < 1 or args.bootstrap < 100 or args.sim_step_seconds != 0.1:
        p.error("seeds >= 1, bootstrap >= 100, sim-step-seconds must equal engine dt=0.1")
    checkpoint = str(args.checkpoint.resolve())
    dqn_checkpoint = str(args.dqn_checkpoint.resolve()) if args.dqn_checkpoint else None
    # Fail before creating output artifacts when weights are missing/incompatible.
    make_controller("d3qn", checkpoint)
    if args.uq_calibration:
        make_controller("flowsync_uq", checkpoint, calibration_path=str(args.uq_calibration.resolve()))
    if dqn_checkpoint:
        make_controller("dqn", checkpoint, dqn_checkpoint)
    else:
        print("Plain DQN omitted: no separately trained --dqn-checkpoint supplied.")
    manifest = args.seed_manifest if args.seed_manifest.is_absolute() else ROOT / args.seed_manifest
    seeds = manifest_seeds(manifest, nseed)
    run_dir = (args.output_dir if args.output_dir is not None else
               Path("results") / "headless" / f"{args.suite}_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}")
    run_dir = run_dir if run_dir.is_absolute() else ROOT / run_dir
    run_dir.mkdir(parents=True, exist_ok=True)
    config = {
        "suite": args.suite, "seeds": seeds, "sim_step_seconds": args.sim_step_seconds,
        "bootstrap": args.bootstrap, "min_seeds_for_inference": args.min_seeds_for_inference,
        "record_trajectories": args.record_trajectories, "git": git_info(),
        "checkpoint": checkpoint, "dqn_checkpoint": dqn_checkpoint,
        "checkpoint_sha256": hashlib.sha256(Path(checkpoint).read_bytes()).hexdigest(),
        "uq_calibration": str(args.uq_calibration.resolve()) if args.uq_calibration else None,
        "uq_calibration_sha256": hashlib.sha256(args.uq_calibration.read_bytes()).hexdigest() if args.uq_calibration else None,
        "dqn_checkpoint_sha256": hashlib.sha256(Path(dqn_checkpoint).read_bytes()).hexdigest() if dqn_checkpoint else None,
        "controllers": args.controllers, "scenarios": args.scenarios, "conditions": args.conditions,
        "evaluation_version": "audited_v2",
        "sensing_assumption": "Shared synthetic count sensor for all adaptive controllers; Fixed ignores sensors",
        "source_hashes": source_digests(),
        "verification_required_before_paper": [
            "Review audit_checks.json, measured safety coverage and per-run checkpoint provenance",
            "Validate synthetic count faults against real camera errors",
            "Calibrate traffic dynamics and incident discharge against independent data",
            "Check model training/test split and OOD isolation",
            "Calibrate uncertainty and thresholds on validation data, not held-out tests",
            "Repeat with independently trained policy seeds, not only traffic seeds",
            "Establish training, headless and web controller/FSM parity",
            "Do not interpret simulator signal checks as hardware or collision certification",
        ],
    }
    config_file = run_dir / "configuration.json"
    csv_file = run_dir / "raw_runs.csv"
    if args.resume:
        if not config_file.is_file() or not csv_file.is_file():
            p.error("--resume requires configuration.json and raw_runs.csv in --output-dir")
        old = json.loads(config_file.read_text(encoding="utf-8"))
        # Require both the settings and code snapshot to match before resuming.
        # Untracked output files can change git dirty-state after a run starts.
        # Compare stable commit and source hashes, but not that volatile boolean.
        old_cmp, new_cmp = json.loads(json.dumps(old)), json.loads(json.dumps(config))
        old_cmp.get("git", {}).pop("dirty", None)
        new_cmp.get("git", {}).pop("dirty", None)
        if old_cmp != new_cmp:
            p.error("Resume configuration, source code, or git commit changed; use a new output directory")
    else:
        if config_file.exists() or csv_file.exists():
            p.error("Output directory already contains run artifacts; use --resume or new directory")
        config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")
    completed: set[tuple] = set()
    if csv_file.exists():
        with csv_file.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["status"] == "ok":
                    completed.add((row["suite"], row["scenario"], row["condition"],
                                   int(row["seed"]), row["controller"]))
    total_jobs = list(jobs(args.suite, seeds))
    if dqn_checkpoint is None:
        total_jobs = [job for job in total_jobs if job[4] != "dqn"]
    for selection, index in ((args.controllers, 4), (args.scenarios, 1), (args.conditions, 2)):
        if selection:
            allowed = set(selection.split(","))
            total_jobs = [job for job in total_jobs if job[index] in allowed]
    if not total_jobs:
        p.error("Filters select no experiments")
    print(f"FlowSync headless evaluation: {len(total_jobs)} planned runs; {len(completed)} resumed.\nOutput: {run_dir}", flush=True)
    failed = 0
    with csv_file.open("a", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=FIELDS)
        if out.tell() == 0:
            writer.writeheader()
        for ix, job in enumerate(total_jobs, start=1):
            if job in completed:
                continue
            row = evaluate_one(job, args.sim_step_seconds, args.record_trajectories,
                               checkpoint, dqn_checkpoint, run_dir / "bundles",
                               str(args.uq_calibration.resolve()) if args.uq_calibration else None)
            writer.writerow(row)
            out.flush()  # Preserve raw evidence even if a later simulation fails.
            if row["status"] != "ok":
                failed += 1
                print(f"[{ix}/{len(total_jobs)}] FAILED: {job} -> {row['error']}", flush=True)
                if not args.continue_on_error:
                    break
            elif ix % 10 == 0 or ix == len(total_jobs):
                print(f"[{ix}/{len(total_jobs)}] {job} avg_delay={row['avg_delay_s']:.3f}s", flush=True)
    with csv_file.open(newline="", encoding="utf-8") as f:
        attempts = list(csv.DictReader(f))
    # Resuming a failed job creates a new attempt. Use only its LAST outcome
    # in the tables, keeping all attempts in the append-only CSV audit trail.
    latest = {}
    for row in attempts:
        key = (row["suite"], row["scenario"], row["condition"],
               int(row["seed"]), row["controller"])
        latest[key] = row
    raw = list(latest.values())
    summaries, comparisons = analyze(raw, args.bootstrap, args.min_seeds_for_inference)
    degradation = noise_degradation(raw, args.bootstrap)
    # Identical clean traffic seeds should reproduce across independently run suites.
    clean_lookup = {(r["scenario"], r["seed"], r["controller"]): float(r["avg_delay_s"])
                    for r in raw if r["suite"] == "clean" and r["status"] == "ok"}
    determinism_checks = []
    for r in raw:
        if r["suite"] == "robustness" and r["condition"] == "clean" and r["status"] == "ok":
            key = (r["scenario"], r["seed"], r["controller"])
            if key in clean_lookup:
                other = float(r["avg_delay_s"])
                determinism_checks.append({"scenario": key[0], "seed": key[1],
                                           "controller": key[2],
                                           "agrees": bool(math.isclose(clean_lookup[key], other,
                                                                       rel_tol=1e-8, abs_tol=1e-8))})
    (run_dir / "determinism_checks.json").write_text(
        json.dumps(determinism_checks, indent=2), encoding="utf-8")
    arrivals_by_pair = defaultdict(set)
    learned_rows = []
    for row in raw:
        if row["status"] != "ok":
            continue
        arrivals_by_pair[(row["scenario"], row["seed"])].add(row["arrival_trace_hash"])
        if row["controller"] not in ("fixed", "greedy", "actuated", "max_pressure"):
            learned_rows.append(row)
    audit_checks = {
        "arrival_traces_match_across_controllers_and_noise": all(
            len(hashes) == 1 and "" not in hashes for hashes in arrivals_by_pair.values()),
        "learning_runs_have_exact_checkpoint_provenance": all(
            row["checkpoint_hash"] == (config["dqn_checkpoint_sha256"] if row["controller"] == "dqn"
                                       else config["checkpoint_sha256"]) for row in learned_rows),
        "safety_sample_counts": sorted({r["safety_samples"] for r in raw if r["status"] == "ok"}),
        "fallback_by_run": [{k: r[k] for k in ("suite", "condition", "seed", "controller", "fallback_steps", "fallback_activations", "shield_interventions")}
                            for r in raw if r["status"] == "ok" and (r["controller"] == "flowsync_uq" or r["suite"] == "ablation")],
        "safety_scope": "Simulator signal conflicts/clearance only; not collision or hardware certification",
    }
    (run_dir / "audit_checks.json").write_text(json.dumps(audit_checks, indent=2), encoding="utf-8")
    write_csv(run_dir / "summary_by_scenario.csv", summaries)
    write_csv(run_dir / "paired_comparisons.csv", comparisons)
    write_csv(run_dir / "noise_degradation.csv", degradation)
    (run_dir / "statistical_report.json").write_text(
        json.dumps({"summaries": summaries, "comparisons": comparisons,
                    "noise_degradation": degradation,
                    "unique_runs": len(raw), "raw_attempt_rows": len(attempts),
                    "successful": sum(r["status"] == "ok" for r in raw),
                    "failed": sum(r["status"] != "ok" for r in raw),
                    "determinism_checks_pass": (all(c["agrees"] for c in determinism_checks)
                                                 if determinism_checks else None),
                    "publication_ready": False,
                    "reason": "Synthetic sensor/simulator validation, UQ calibration, training provenance and independent held-out replication remain required",
                    "audit_checks": audit_checks},
                   indent=2, allow_nan=False), encoding="utf-8")
    latex_table(run_dir / "table_clean.tex", summaries, "clean", "test_clean_balanced_01", "clean",
                "Controller performance on held-out clean traffic")
    latex_table(run_dir / "table_robustness.tex", summaries, "robustness", "test_clean_balanced_01", "miss_30",
                "Controller performance with 30% missed detections")
    latex_table(run_dir / "table_ablations.tex", summaries, "ablation", "test_clean_balanced_01", "ablation_faults",
                "FlowSync-UQ component ablation under perception faults")
    print(f"Completed: {sum(r['status']=='ok' for r in raw)}/{len(total_jobs)}; "
          f"failed rows: {sum(r['status']!='ok' for r in raw)}. Saved reports to {run_dir}")
    successful_keys = {(r["suite"], r["scenario"], r["condition"],
                        int(r["seed"]), r["controller"]) for r in raw if r["status"] == "ok"}
    if any(not c["agrees"] for c in determinism_checks):
        raise SystemExit("Determinism mismatch: inspect determinism_checks.json")
    if not audit_checks["arrival_traces_match_across_controllers_and_noise"] or not audit_checks["learning_runs_have_exact_checkpoint_provenance"]:
        raise SystemExit("Provenance/CRN audit failed: inspect audit_checks.json")
    if failed or any(j not in successful_keys for j in total_jobs):
        raise SystemExit("Incomplete/failed run matrix: inspect raw_runs.csv; use --resume after fixing")


if __name__ == "__main__":
    main()
