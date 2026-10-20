"""
run_experiments_matrix.py — End-to-End Primary Experiment Matrix and Analysis
=============================================================================
Executes the Phase H / Phase I / Phase K primary experimental matrix across
all 7 controllers, clean and degraded perception conditions, and multiple
paired CRN seeds. Automatically computes statistical hypothesis tests
(Wilcoxon, t-test, bootstrap 95% CIs, Cohen's d, Cliff's delta, Holm-Bonferroni)
and generates publication LaTeX tables and CSV reports.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

from server.app.controllers import get_controller
from research.noise.fault_injector import PerceptionFaultInjector, FaultProfile
from research.experiments.engine import ExperimentRunner, ExperimentResult
from research.analysis.statistical_pipeline import (
    adjust_p_values_holm_bonferroni,
    paired_difference_analysis,
)
from research.analysis.table_generator import TableGenerator
from research.run_suite import load_scenario

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("experiments_matrix")


NOISE_CONDITIONS: Dict[str, Optional[FaultProfile]] = {
    "clean": None,
    "miss_10": FaultProfile(name="miss_10", miss_rate=0.10),
    "miss_20": FaultProfile(name="miss_20", miss_rate=0.20),
    "latency_250ms": FaultProfile(name="latency_250ms", latency_ms=250),
    "combined": FaultProfile(
        name="combined_moderate",
        miss_rate=0.15,
        latency_ms=200,
        false_positive_lambda=0.10,
        jitter_std=0.02,
    ),
}


def run_matrix_benchmark(
    scenario_ids: List[str],
    controller_names: List[str],
    condition_names: List[str],
    seeds: List[int],
    results_dir: Path = Path("results"),
    output_tables_dir: Path = Path("results/tables"),
) -> Dict[str, Any]:
    """
    Executes full paired benchmark matrix across controllers, conditions, and seeds.
    """
    runner = ExperimentRunner()
    results: List[ExperimentResult] = []

    total_runs = len(scenario_ids) * len(controller_names) * len(condition_names) * len(seeds)
    logger.info(
        "Beginning Experiment Matrix: %d scenarios, %d controllers, %d conditions, %d seeds (%d total runs)",
        len(scenario_ids), len(controller_names), len(condition_names), len(seeds), total_runs,
    )

    tagged_results: List[Tuple[str, ExperimentResult]] = []

    run_idx = 0
    for sc_id in scenario_ids:
        scenario = load_scenario(sc_id)
        for cond_name in condition_names:
            fault_prof = NOISE_CONDITIONS.get(cond_name)
            fault_inj = PerceptionFaultInjector(fault_prof) if fault_prof else None

            for seed in seeds:
                if fault_inj:
                    fault_inj.reset_seed(seed + 50000)

                for c_name in controller_names:
                    run_idx += 1
                    ctrl = get_controller(c_name)
                    exp_res = runner.run(
                        controller=ctrl,
                        scenario=scenario,
                        seed=seed,
                        record_trajectory=False,
                        fault_injector=fault_inj,
                    )
                    tagged_results.append((cond_name, exp_res))
                    results.append(exp_res)
                    logger.info(
                        "[%d/%d] %s | %s | %s | s=%d -> Delay=%.2fs, QArea=%.1f",
                        run_idx, total_runs, sc_id, cond_name, c_name, seed,
                        exp_res.avg_delay, exp_res.queue_area,
                    )

    # 1. Aggregate main comparison (clean condition across all seeds)
    main_records: List[Dict[str, Any]] = []
    for c_name in controller_names:
        c_runs = [res for cond, res in tagged_results if res.controller_name == c_name and cond == "clean"]
        if not c_runs:
            c_runs = [res for cond, res in tagged_results if res.controller_name == c_name]
        delays = [r.avg_delay for r in c_runs]
        p95s = [r.p95_delay for r in c_runs]
        qas = [r.queue_area for r in c_runs]
        tps = [r.total_vehicles_passed / (r.num_steps * 0.1) * 3600.0 for r in c_runs]
        fbs = [r.watchdog_override_rate for r in c_runs]
        shields = [r.watchdog_override_count for r in c_runs]

        main_records.append({
            "controller": c_name,
            "mean_delay": float(np.mean(delays)),
            "std_delay": float(np.std(delays)),
            "p95_delay": float(np.mean(p95s)),
            "queue_area": float(np.mean(qas)),
            "throughput": float(np.mean(tps)),
            "fallback_rate": float(np.mean(fbs)),
            "shield_interventions": int(np.sum(shields)),
        })

    # Sort so top performing is easily seen
    main_records.sort(key=lambda x: x["mean_delay"])

    # 2. Robustness across noise conditions
    robustness_records: List[Dict[str, Any]] = []
    for c_name in controller_names:
        row: Dict[str, Any] = {"controller": c_name}
        clean_delay = 1.0
        for cond in condition_names:
            matched = [
                res.avg_delay for c_tag, res in tagged_results
                if res.controller_name == c_name and c_tag == cond
            ]
            avg_d = float(np.mean(matched)) if matched else 0.0
            row[f"{cond}_delay"] = avg_d
            if cond == "clean":
                clean_delay = max(avg_d, 0.01)

        worst_delay = max([row.get(f"{cond}_delay", 0.0) for cond in condition_names], default=clean_delay)
        max_deg = max(0.0, (worst_delay - clean_delay) / clean_delay * 100.0)
        row["max_degradation_pct"] = max_deg
        robustness_records.append(row)

    # 3. Statistical Hypothesis Testing vs Baselines
    # Compare candidate "flowsync_uq" vs baseline "d3qn" and "max_pressure"
    stat_comparisons: Dict[str, Any] = {}
    p_values_to_correct: List[float] = []
    comparison_keys: List[str] = []

    for baseline_name in ["d3qn", "max_pressure", "fixed"]:
        if baseline_name not in controller_names or "flowsync_uq" not in controller_names:
            continue

        base_pairs = [(cond, res) for cond, res in tagged_results if res.controller_name == baseline_name]
        cand_pairs = [(cond, res) for cond, res in tagged_results if res.controller_name == "flowsync_uq"]

        matched_base = []
        matched_cand = []
        for b_cond, b_res in base_pairs:
            for c_cond, c_res in cand_pairs:
                if (b_res.scenario_id == c_res.scenario_id and
                    b_res.seed == c_res.seed and
                    b_cond == c_cond):
                    matched_base.append(b_res.avg_delay)
                    matched_cand.append(c_res.avg_delay)
                    break

        if len(matched_base) >= 3:
            stat_res = paired_difference_analysis(
                baseline_values=matched_base,
                candidate_values=matched_cand,
                metric_name="mean_delay",
                higher_is_better=False,
            )
            key = f"flowsync_uq_vs_{baseline_name}"
            stat_comparisons[key] = stat_res.to_dict()
            p_values_to_correct.append(stat_res.recommended_p)
            comparison_keys.append(key)

    # Apply Holm-Bonferroni correction
    if p_values_to_correct:
        adj_p = adjust_p_values_holm_bonferroni(p_values_to_correct)
        for key, ap in zip(comparison_keys, adj_p):
            stat_comparisons[key]["holm_adjusted_p"] = ap
            stat_comparisons[key]["is_significant_after_fwer"] = ap < 0.05

    # 4. Generate Tables and Export
    output_tables_dir.mkdir(parents=True, exist_ok=True)
    TableGenerator.generate_main_benchmark_latex(
        main_records, output_tables_dir / "table_benchmark_comparison.tex"
    )
    TableGenerator.export_csv(
        main_records, output_tables_dir / "table_benchmark_comparison.csv"
    )

    TableGenerator.generate_robustness_latex(
        robustness_records, output_tables_dir / "table_noise_robustness.tex"
    )
    TableGenerator.export_csv(
        robustness_records, output_tables_dir / "table_noise_robustness.csv"
    )

    report_payload = {
        "main_summary": main_records,
        "robustness_summary": robustness_records,
        "statistical_tests": stat_comparisons,
    }
    with open(results_dir / "statistical_report.json", "w") as f:
        json.dump(report_payload, f, indent=2)

    logger.info("Generated benchmark comparison tables and statistical report in %s", output_tables_dir)
    return report_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Run research experiment matrix and statistical pipeline")
    parser.add_argument("--scenarios", type=str, default="train_mod_balanced_01,test_clean_balanced_01")
    parser.add_argument("--controllers", type=str, default="fixed,greedy,max_pressure,d3qn,flowsync_uq")
    parser.add_argument("--conditions", type=str, default="clean,miss_10,miss_20,latency_250ms,combined")
    parser.add_argument("--seeds", type=str, default="101,202,303")
    args = parser.parse_args()

    scenarios = [s.strip() for s in args.scenarios.split(",") if s.strip()]
    controllers = [c.strip() for c in args.controllers.split(",") if c.strip()]
    conditions = [cond.strip() for cond in args.conditions.split(",") if cond.strip()]
    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]

    run_matrix_benchmark(
        scenario_ids=scenarios,
        controller_names=controllers,
        condition_names=conditions,
        seeds=seeds,
    )


if __name__ == "__main__":
    main()
