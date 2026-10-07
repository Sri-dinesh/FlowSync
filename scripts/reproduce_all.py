"""
reproduce_all.py — One-Command Complete IEEE Research Reproduction Suite (Task 14)
===================================================================================
Enables any independent researcher to reproduce all empirical experiments,
statistical hypothesis tests, and publication tables from scratch with a single command.

Usage:
    python scripts/reproduce_all.py --quick
    python scripts/reproduce_all.py --full
    python scripts/reproduce_all.py --final
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict
import torch

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_SERVER = _ROOT / "server"
if str(_SERVER) not in sys.path:
    sys.path.insert(0, str(_SERVER))

from research.run_experiments_matrix import run_matrix_benchmark
from research.experiments.run_ablations import run_ablation_experiments
from research.experiments.run_threshold_sweep import run_threshold_sweep
from research.analysis.failure_analysis import sweep_reliability_boundary
from research.experiments.run_city_scalability import run_scalability_benchmark
from research.profiling.latency_profiler import profile_pipeline_latency
from research.cv.shadow_mode_replay import evaluate_shadow_replay
from research.noise.fault_injector import FaultProfile

from research.experiments.run_final_hardened_experiments import run_final_hardened_experiments
from research.experiments.run_reliability_boundary_v2 import evaluate_reliability_boundary
from research.experiments.run_city_scalability_v2 import run_city_scalability_suite
from research.cv.shadow_mode_multi_session import run_multi_session_shadow_replay
from research.cv.validate_perception_quality import run_cv_validation_evaluation
from research.profiling.full_pipeline_profiler import profile_full_perception_and_control

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reproduce_all")


def compute_sha256(path: Path | str) -> str:
    h = hashlib.sha256()
    p = Path(path)
    if not p.exists():
        return "file_not_found"
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def export_environment_provenance(results_dir: Path) -> Dict[str, Any]:
    """Exports immutable machine environment, git, model hashes, and dependency metadata."""
    results_dir.mkdir(parents=True, exist_ok=True)

    git_commit = "unknown"
    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=_ROOT, text=True
        ).strip()
    except Exception:
        pass

    (results_dir / "git_commit.txt").write_text(git_commit, encoding="utf-8")

    env_info = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_commit": git_commit,
        "os": platform.platform(),
        "python_version": platform.python_version(),
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "model_hashes": {
            "d3qn_checkpoint": compute_sha256(_ROOT / "server/models/d3qn_final_v5.pt"),
            "yolo_detector": compute_sha256(_ROOT / "server/yolov8n.pt"),
            "final_seed_manifest": compute_sha256(_ROOT / "research/manifests/final_seed_manifest_v2.json"),
            "video_sessions_manifest": compute_sha256(_ROOT / "research/manifests/video_sessions_manifest.json"),
        },
    }
    (results_dir / "environment.json").write_text(json.dumps(env_info, indent=2), encoding="utf-8")
    logger.info("Exported provenance: Git=%s, Python=%s, PyTorch=%s", git_commit, platform.python_version(), torch.__version__)
    return env_info


def run_final_submission_reproduction(results_dir: Path) -> None:
    """Executes the complete hardened 20-seed reproduction suite for IEEE submission."""
    t0_final = time.time()
    logger.info("=== FlowSync-UQ Final Submission 20-Seed Reproduction Initiated ===")
    results_dir.mkdir(parents=True, exist_ok=True)
    provenance = export_environment_provenance(results_dir)

    manifest_path = _ROOT / "research/manifests/final_seed_manifest_v2.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    seeds = manifest.get("seeds", list(range(1101, 1121)))

    logger.info(">>> Stage 1/6: Final 20-Seed Clean Benchmark, Robustness, Ablations, and Stats...")
    run_final_hardened_experiments(seeds=seeds, output_dir=results_dir)

    logger.info(">>> Stage 2/6: Full Camera-to-Control Real-Time Latency Profiler...")
    profile_full_perception_and_control(num_frames=1000, warmup_frames=100, output_dir=results_dir)

    logger.info(">>> Stage 3/6: Computer Vision / Perception Quality Validation...")
    run_cv_validation_evaluation(output_dir=results_dir)

    logger.info(">>> Stage 4/6: Multi-Session Empirical CCTV Shadow Replay...")
    run_multi_session_shadow_replay(output_dir=results_dir)

    logger.info(">>> Stage 5/6: Empirical Reliability Boundary Sweep (20 Seeds)...")
    evaluate_reliability_boundary(seeds=seeds, output_dir=results_dir)

    logger.info(">>> Stage 6/6: Multi-Intersection 2x2 Network Scalability (20 Seeds)...")
    run_city_scalability_suite(seeds=seeds, output_dir=results_dir)

    total_time = time.time() - t0_final
    summary = {
        "status": "COMPLETED",
        "total_runtime_seconds": round(total_time, 2),
        "provenance": provenance,
        "generated_tables": [
            "table_benchmark_comparison_v2.tex",
            "table_noise_robustness_v2.tex",
            "table_ablations_v2.tex",
            "table_reliability_boundary_v2.tex",
            "table_city_2x2_scalability_v2.tex",
            "table_shadow_replay_v2.tex",
            "table_latency_profile_full.tex",
            "table_cv_perception_validation.tex",
        ],
    }
    (results_dir / "reproduction_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    logger.info("=== FlowSync-UQ Final Submission Suite Successfully Reproduced in %.1fs ===", total_time)


def main() -> None:
    parser = argparse.ArgumentParser(description="One-command reproduction of all FlowSync IEEE benchmark experiments")
    parser.add_argument("--quick", action="store_true", help="Run fast verification suite (2 seeds, subset of conditions)")
    parser.add_argument("--full", action="store_true", help="Run full comprehensive research evaluation")
    parser.add_argument("--final", action="store_true", help="Run frozen 20-seed final IEEE submission reproduction suite")
    parser.add_argument("--output-dir", type=str, default="")
    args = parser.parse_args()

    if args.final:
        out_dir = Path(args.output_dir) if args.output_dir else Path("results/final")
        run_final_submission_reproduction(out_dir)
        return

    results_dir = Path(args.output_dir) if args.output_dir else Path("results")
    export_environment_provenance(results_dir)

    seeds = [101, 202] if args.quick or not args.full else [101, 202, 303, 404, 505]
    logger.info("=== FlowSync IEEE Research Suite Reproduction Initiated (seeds=%s) ===", seeds)

    t0_all = time.time()

    # 1. Primary Controller Matrix & Statistical Analysis (Phase H, I, K)
    logger.info(">>> Stage 1/7: Primary Experiment Matrix and Statistical Tests...")
    run_matrix_benchmark(
        scenario_ids=["train_mod_balanced_01", "test_clean_balanced_01"],
        controller_names=["fixed", "greedy", "max_pressure", "d3qn", "flowsync_uq"],
        condition_names=["clean", "miss_20", "latency_250ms"],
        seeds=seeds,
        results_dir=results_dir,
        output_tables_dir=results_dir / "tables",
    )

    # 2. Component Ablations
    logger.info(">>> Stage 2/7: Component Ablations Study...")
    ablation_noise = FaultProfile(name="ablation_noise", miss_rate=0.20, latency_ms=150)
    run_ablation_experiments(
        scenario_ids=["train_mod_balanced_01", "test_clean_balanced_01"],
        seeds=seeds,
        noise_profile=ablation_noise,
        results_dir=results_dir / "ablations",
    )

    # 3. Threshold Sensitivity Sweep
    logger.info(">>> Stage 3/7: Fallback Uncertainty Threshold Sensitivity...")
    run_threshold_sweep(
        scenario_ids=["train_mod_balanced_01"],
        seeds=seeds[:2],
        thresholds=[0.10, 0.25, 0.40, 0.50, 0.65, 0.80, 0.95],
        noise_profile=FaultProfile(name="sweep_noise", miss_rate=0.20, latency_ms=100),
        results_dir=results_dir / "sensitivity",
    )

    # 4. Failure Analysis & Reliability Boundary
    logger.info(">>> Stage 4/7: Reliability Boundary & Failure Taxonomy...")
    sweep_reliability_boundary(
        scenario_id="train_mod_balanced_01",
        seeds=seeds[:2],
        miss_rates=[0.0, 0.10, 0.20, 0.40],
        controllers=["d3qn", "flowsync_uq", "max_pressure"],
        results_dir=results_dir / "reliability",
    )

    # 5. Multi-Intersection Scalability
    logger.info(">>> Stage 5/7: 2x2 City Network Multi-Intersection Scalability...")
    run_scalability_benchmark(
        controller_names=["fixed", "greedy", "max_pressure", "d3qn", "flowsync_uq"],
        seeds=seeds[:2],
        duration_steps=400 if args.quick else 600,
        results_dir=results_dir / "scalability",
    )

    # 6. Real-Time Latency Profiling
    logger.info(">>> Stage 6/7: Real-Time Performance Profiling...")
    num_decisions = 1000 if args.quick else 10000
    profile_pipeline_latency(
        num_decisions=num_decisions,
        warmup_steps=100,
        results_dir=results_dir / "profiling",
    )

    # 7. Shadow-Mode Real CCTV Replay
    logger.info(">>> Stage 7/7: Real-World CCTV Shadow-Mode Replay...")
    evaluate_shadow_replay(
        controller_names=["fixed", "greedy", "max_pressure", "d3qn", "flowsync_uq"],
        seeds=seeds[:2],
        duration_steps=600 if args.quick else 1200,
        results_dir=results_dir / "shadow_mode",
    )

    total_time = time.time() - t0_all
    logger.info("=== FlowSync IEEE Research Suite Reproduction Complete in %.1fs ===", total_time)
    logger.info("All publication tables generated in %s/tables and respective subdirectories.", results_dir)


if __name__ == "__main__":
    main()
