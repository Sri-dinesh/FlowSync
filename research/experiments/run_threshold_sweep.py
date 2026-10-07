"""
run_threshold_sweep.py — Uncertainty Threshold Sensitivity Study (Phase J / Task J2)
===================================================================================
Sweeps fallback uncertainty threshold theta_uq across [0.10, 0.25, 0.40, 0.50, 0.65, 0.80, 0.95]
to evaluate stability, fallback rate, delay, and safety across operational regimes.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List
import numpy as np

from server.app.controllers.flowsync_uq import FlowSyncUQController
from research.noise.fault_injector import PerceptionFaultInjector, FaultProfile
from research.experiments.engine import ExperimentRunner
from research.analysis.table_generator import TableGenerator
from research.run_suite import load_scenario

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("threshold_sweep")

DEFAULT_THRESHOLDS = [0.10, 0.25, 0.40, 0.50, 0.65, 0.80, 0.95]


def run_threshold_sweep(
    scenario_ids: List[str],
    seeds: List[int],
    thresholds: List[float] = DEFAULT_THRESHOLDS,
    noise_profile: Optional[FaultProfile] = None,
    results_dir: Path = Path("results/sensitivity"),
) -> List[Dict[str, Any]]:
    """
    Executes uncertainty threshold sensitivity sweep.
    """
    results_dir.mkdir(parents=True, exist_ok=True)
    runner = ExperimentRunner()
    records: List[Dict[str, Any]] = []

    for theta in thresholds:
        logger.info("Evaluating Threshold theta_uq = %.2f", theta)
        ctrl = FlowSyncUQController(uncertainty_threshold=theta, enable_shield=True)

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
                    fault_inj.reset(seed + 2000)

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
            "theta_uq": theta,
            "mean_delay": float(np.mean(delays)),
            "std_delay": float(np.std(delays)),
            "p95_delay": float(np.mean(p95s)),
            "queue_area": float(np.mean(qas)),
            "throughput": float(np.mean(tps)),
            "fallback_rate_pct": float(np.mean(fbs) * 100.0),
            "shield_interventions": int(np.sum(shields)),
        })

    csv_path = results_dir / "table_threshold_sweep.csv"
    TableGenerator.export_csv(records, csv_path)
    json_path = results_dir / "threshold_sensitivity.json"
    json_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    logger.info("Saved threshold sensitivity report: %s, %s", csv_path, json_path)
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Run uncertainty threshold sensitivity sweep")
    parser.add_argument("--scenarios", type=str, default="train_mod_balanced_01,test_clean_balanced_01")
    parser.add_argument("--seeds", type=str, default="101,202")
    parser.add_argument("--miss-rate", type=float, default=0.20)
    args = parser.parse_args()

    scenarios = [s.strip() for s in args.scenarios.split(",") if s.strip()]
    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    noise = FaultProfile(name="sweep_noise", miss_rate=args.miss_rate, latency_ms=100)

    run_threshold_sweep(scenarios, seeds, noise_profile=noise)


if __name__ == "__main__":
    main()
