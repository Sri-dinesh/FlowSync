"""
run_ablations.py — Component Ablation Study (Phase J / Task J1)
==============================================================
Evaluates the contribution of each FlowSync-UQ architectural component:
1. Full FlowSync-UQ (D3QN + UQ + Shield + Supervisor + MaxPressure Fallback)
2. minus Uncertainty Estimator (No UQ: threshold set to infinity, fallback never called)
3. minus Safety Shield (No Shield: raw policy actions executed without constraints)
4. minus Fallback (No Fallback: keeps executing D3QN under corruption)
5. minus Max-Pressure Fallback (Fixed cycle fallback instead of Max-Pressure)
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

from server.app.controllers.flowsync_uq import FlowSyncUQController
from research.noise.fault_injector import PerceptionFaultInjector, FaultProfile
from research.experiments.engine import ExperimentRunner
from research.analysis.table_generator import TableGenerator
from research.run_suite import load_scenario

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ablations")


def build_ablation_controllers() -> Dict[str, FlowSyncUQController]:
    """Instantiates each ablated variant of FlowSync-UQ."""
    return {
        "Full FlowSync-UQ": FlowSyncUQController(
            uncertainty_threshold=0.45,
            enable_shield=True,
            fallback_controller_name="max_pressure",
        ),
        "minus Uncertainty (No-UQ)": FlowSyncUQController(
            uncertainty_threshold=999.0,  # Never triggers fallback
            enable_shield=True,
            fallback_controller_name="max_pressure",
        ),
        "minus Safety Shield (No-Shield)": FlowSyncUQController(
            uncertainty_threshold=0.45,
            enable_shield=False,
            fallback_controller_name="max_pressure",
        ),
        "minus Fallback (No-Fallback)": FlowSyncUQController(
            uncertainty_threshold=0.45,
            enable_shield=True,
            fallback_controller_name="d3qn",  # Falls back to pure D3QN
        ),
        "minus MaxPressure (Fixed Fallback)": FlowSyncUQController(
            uncertainty_threshold=0.45,
            enable_shield=True,
            fallback_controller_name="fixed",  # Falls back to Webster fixed
        ),
    }


def run_ablation_experiments(
    scenario_ids: List[str],
    seeds: List[int],
    noise_profile: Optional[FaultProfile] = None,
    results_dir: Path = Path("results/ablations"),
) -> List[Dict[str, Any]]:
    """
    Executes controlled paired ablations.
    """
    results_dir.mkdir(parents=True, exist_ok=True)
    runner = ExperimentRunner()
    variants = build_ablation_controllers()

    records: List[Dict[str, Any]] = []

    for name, ctrl in variants.items():
        logger.info("Evaluating Ablation Variant: %s", name)
        delays = []
        p95s = []
        qas = []
        tps = []
        fbs = []
        shields = []

        for sc_id in scenario_ids:
            scenario = load_scenario(sc_id)
            for seed in seeds:
                fault_inj = PerceptionFaultInjector(noise_profile) if noise_profile else None
                if fault_inj:
                    fault_inj.reset(seed + 1000)

                res = runner.run(
                    controller=ctrl,
                    scenario=scenario,
                    seed=seed,
                    record_trajectory=False,
                    fault_injector=fault_inj,
                )
                delays.append(res.avg_delay)
                p95s.append(res.p95_delay)
                qas.append(res.queue_area)
                tps.append(res.total_vehicles_passed / (res.num_steps * 0.1) * 3600.0)
                fbs.append(res.watchdog_override_rate)
                shields.append(res.watchdog_override_count)

        records.append({
            "variant": name,
            "mean_delay": float(np.mean(delays)),
            "std_delay": float(np.std(delays)),
            "p95_delay": float(np.mean(p95s)),
            "queue_area": float(np.mean(qas)),
            "throughput": float(np.mean(tps)),
            "fallback_rate": float(np.mean(fbs)),
            "shield_interventions": int(np.sum(shields)),
        })

    # Export LaTeX and CSV
    tex_path = results_dir / "table_ablations.tex"
    csv_path = results_dir / "table_ablations.csv"

    # Generate custom LaTeX table
    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Component Ablation Study Under Perception Disturbance}",
        r"\label{tab:ablation_study}",
        r"\begin{tabular}{lccccc}",
        r"\toprule",
        r"\textbf{Ablation Variant} & \textbf{Mean Delay (s)} & \textbf{P95 Delay (s)} & \textbf{Queue-Area (veh$\cdot$s)} & \textbf{Throughput (veh/h)} & \textbf{Shield Int.} \\",
        r"\midrule",
    ]
    for r in records:
        v_name = r["variant"]
        delay = f"{r['mean_delay']:.2f} $\\pm$ {r['std_delay']:.2f}"
        p95 = f"{r['p95_delay']:.2f}"
        qa = f"{r['queue_area']:.1f}"
        tp = f"{r['throughput']:.1f}"
        s_int = f"{r['shield_interventions']}"
        if "Full FlowSync-UQ" in v_name:
            lines.append(f"\\textbf{{{v_name}}} & \\textbf{{{delay}}} & \\textbf{{{p95}}} & \\textbf{{{qa}}} & \\textbf{{{tp}}} & {s_int} \\\\")
        else:
            lines.append(f"{v_name} & {delay} & {p95} & {qa} & {tp} & {s_int} \\\\")
    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table*}",
    ])
    tex_path.write_text("\n".join(lines), encoding="utf-8")

    TableGenerator.export_csv(records, csv_path)
    logger.info("Saved ablation report: %s, %s", tex_path, csv_path)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Run component ablation experiments")
    parser.add_argument("--scenarios", type=str, default="train_mod_balanced_01,test_clean_balanced_01")
    parser.add_argument("--seeds", type=str, default="101,202,303")
    parser.add_argument("--miss-rate", type=float, default=0.20)
    args = parser.parse_args()

    scenarios = [s.strip() for s in args.scenarios.split(",") if s.strip()]
    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    noise = FaultProfile(name="ablation_noise", miss_rate=args.miss_rate, latency_ms=150)

    run_ablation_experiments(scenarios, seeds, noise)


if __name__ == "__main__":
    main()
