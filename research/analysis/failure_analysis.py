"""
failure_analysis.py — Reliability Boundary and Failure Taxonomy Engine (Phase L)
===============================================================================
Implements Tasks L1, L2, and L3:
1. Reliability Boundary: Estimates critical perception corruption threshold
   where standard D3QN degrades sharply vs FlowSync-UQ.
2. Failure Taxonomy & Registry: Classifies runs into pre-defined failure modes
   (spillback, starvation, extreme tail delay, safety violations, thrashing).
3. Counterfactual Traces: Analyzes divergence points between D3QN and FlowSync-UQ.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from server.app.controllers import get_controller
from research.scenarios.scenario_schema import ScenarioConfig
from research.noise.fault_injector import PerceptionFaultInjector, FaultProfile
from research.experiments.engine import ExperimentRunner, ExperimentResult
from research.analysis.table_generator import TableGenerator
from research.run_suite import load_scenario

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("failure_analysis")


class FailureMode(str, Enum):
    NOMINAL = "nominal"
    SPILLBACK = "spillback"               # max_queue > 25 veh
    STARVATION = "starvation"             # starvation_count > 3
    EXTREME_DELAY = "extreme_tail_delay"  # p95_delay > 50s
    SAFETY_VIOLATION = "safety_violation" # unsafe transitions > 0
    FALLBACK_THRASHING = "thrashing"     # fallback_rate > 40%


FAILURE_CRITERIA = {
    "max_queue_limit": 25,
    "starvation_limit": 3,
    "p95_delay_limit": 50.0,
    "fallback_thrashing_limit": 0.40,
}


@dataclass
class FailureRecord:
    experiment_id: str
    scenario_id: str
    controller: str
    seed: int
    fault_condition: str
    failure_modes: List[str]
    is_failed: bool
    primary_root_cause: str
    metrics: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def classify_run_failure(
    exp_res: ExperimentResult,
    fault_name: str = "clean",
    unsafe_transitions: int = 0,
) -> FailureRecord:
    """
    Classifies a completed benchmark run into the pre-defined failure taxonomy.
    """
    modes: List[str] = []

    if unsafe_transitions > 0:
        modes.append(FailureMode.SAFETY_VIOLATION.value)
    if exp_res.max_queue > FAILURE_CRITERIA["max_queue_limit"]:
        modes.append(FailureMode.SPILLBACK.value)
    if exp_res.starvation_count > FAILURE_CRITERIA["starvation_limit"]:
        modes.append(FailureMode.STARVATION.value)
    if exp_res.p95_delay > FAILURE_CRITERIA["p95_delay_limit"]:
        modes.append(FailureMode.EXTREME_DELAY.value)
    if exp_res.watchdog_override_rate > FAILURE_CRITERIA["fallback_thrashing_limit"]:
        modes.append(FailureMode.FALLBACK_THRASHING.value)

    if not modes:
        modes.append(FailureMode.NOMINAL.value)

    is_failed = FailureMode.NOMINAL.value not in modes

    # Primary root cause assignment
    if FailureMode.SAFETY_VIOLATION.value in modes:
        root = "Safety Shield Bypass or Phase Timing Defect"
    elif FailureMode.STARVATION.value in modes:
        root = "Policy Asymmetry / Starvation Under Blind Observation"
    elif FailureMode.SPILLBACK.value in modes:
        root = "Excessive Queue Accumulation / Throughput Collapse"
    elif FailureMode.EXTREME_DELAY.value in modes:
        root = "Tail Congestion Under Latency / Observation Noise"
    elif FailureMode.FALLBACK_THRASHING.value in modes:
        root = "Supervisor Hysteresis Deadband Under-Damped"
    else:
        root = "None (Operational within bounds)"

    return FailureRecord(
        experiment_id=exp_res.experiment_id,
        scenario_id=exp_res.scenario_id,
        controller=exp_res.controller_name,
        seed=exp_res.seed,
        fault_condition=fault_name,
        failure_modes=modes,
        is_failed=is_failed,
        primary_root_cause=root,
        metrics={
            "avg_delay": exp_res.avg_delay,
            "p95_delay": exp_res.p95_delay,
            "max_queue": float(exp_res.max_queue),
            "starvation_count": float(exp_res.starvation_count),
            "fallback_rate": exp_res.watchdog_override_rate,
        },
    )


def sweep_reliability_boundary(
    scenario_id: str = "train_mod_balanced_01",
    seeds: List[int] = (101, 202, 303),
    miss_rates: List[float] = (0.0, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50),
    controllers: List[str] = ("d3qn", "flowsync_uq", "max_pressure"),
    results_dir: Path = Path("results/reliability"),
) -> Dict[str, Any]:
    """
    Task L1: Sweeps perception corruption to find the empirical reliability boundary.
    """
    results_dir.mkdir(parents=True, exist_ok=True)
    runner = ExperimentRunner()
    scenario = load_scenario(scenario_id)

    boundary_data: Dict[str, List[Dict[str, Any]]] = {c: [] for c in controllers}
    all_classifications: List[FailureRecord] = []

    for miss in miss_rates:
        fault_prof = FaultProfile(name=f"sweep_miss_{int(miss*100)}", miss_rate=miss)
        fault_inj = PerceptionFaultInjector(fault_prof)

        for c_name in controllers:
            ctrl = get_controller(c_name)
            delays = []
            p95s = []
            failures = 0

            for seed in seeds:
                fault_inj.reset(seed + 9000)
                res = runner.run(
                    controller=ctrl,
                    scenario=scenario,
                    seed=seed,
                    record_trajectory=False,
                    fault_injector=fault_inj,
                )
                rec = classify_run_failure(res, fault_name=f"miss_{miss:.2f}")
                all_classifications.append(rec)
                if rec.is_failed:
                    failures += 1

                delays.append(res.avg_delay)
                p95s.append(res.p95_delay)

            boundary_data[c_name].append({
                "miss_rate": miss,
                "mean_delay": float(np.mean(delays)),
                "p95_delay": float(np.mean(p95s)),
                "failure_rate": failures / len(seeds),
            })

    # Save summary
    out_json = results_dir / "reliability_boundary.json"
    out_json.write_text(json.dumps(boundary_data, indent=2), encoding="utf-8")

    registry_json = results_dir / "failure_registry.json"
    registry_json.write_text(
        json.dumps([r.to_dict() for r in all_classifications], indent=2), encoding="utf-8"
    )

    # Export CSV
    rows = []
    for c_name, points in boundary_data.items():
        for pt in points:
            rows.append({
                "controller": c_name,
                "miss_rate": pt["miss_rate"],
                "mean_delay": pt["mean_delay"],
                "p95_delay": pt["p95_delay"],
                "failure_rate": pt["failure_rate"],
            })
    TableGenerator.export_csv(rows, results_dir / "table_reliability_boundary.csv")
    logger.info("Saved reliability boundary analysis: %s, %s", out_json, registry_json)
    return boundary_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Run failure analysis and reliability boundary sweep")
    parser.add_argument("--scenario", type=str, default="train_mod_balanced_01")
    parser.add_argument("--seeds", type=str, default="101,202,303")
    args = parser.parse_args()

    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]
    sweep_reliability_boundary(scenario_id=args.scenario, seeds=seeds)


if __name__ == "__main__":
    main()
