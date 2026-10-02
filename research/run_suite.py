"""
run_suite.py — Headless Research Benchmark Suite Runner CLI
============================================================
Runs paired, multi-seed comparative benchmark experiments across
registered traffic controllers and frozen scenarios.

Usage Examples:
    python -m research.run_suite --scenario train_mod_balanced_01 --controllers fixed,greedy,max_pressure --seeds 42,1337
    python -m research.run_suite --suite smoke --controllers fixed,max_pressure,d3qn
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

# Ensure repository root and server/ are on sys.path
_ROOT = Path(__file__).resolve().parent.parent
_SERVER = _ROOT / "server"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_SERVER) not in sys.path:
    sys.path.insert(0, str(_SERVER))

from server.app.controllers import get_controller, BaseController, CONTROLLER_REGISTRY
from research.scenarios.scenario_schema import ScenarioConfig
from research.experiments.engine import ExperimentRunner, ExperimentResult

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("run_suite")

SCENARIO_MANIFEST_PATH = Path("research/scenarios/manifest.json")
RESULTS_DIR = Path("results")

DEFAULT_SUITES: Dict[str, List[str]] = {
    "smoke": ["train_mod_balanced_01"],
    "baselines": ["train_low_balanced_01", "train_mod_balanced_01", "train_high_balanced_01", "train_ns_asymmetric_01"],
    "validation": ["val_oversaturated_01", "val_turning_heavy_01", "val_rush_hour_ramp_01"],
    "test_clean": ["test_clean_balanced_01"],
    "test_stress": ["test_near_gridlock_01", "test_left_turn_surge_01", "test_sudden_burst_01", "test_demand_reversal_01", "test_incident_reduction_01", "test_heldout_ood_01"],
}


def parse_seeds(seed_arg: str) -> List[int]:
    """Parse comma-separated seeds or range '1000:1005'."""
    seeds = []
    for part in seed_arg.split(","):
        part = part.strip()
        if ":" in part:
            start, end = part.split(":")
            seeds.extend(range(int(start), int(end) + 1))
        elif part:
            seeds.append(int(part))
    return seeds


def load_scenario(identifier: str) -> ScenarioConfig:
    """Load scenario by ID from manifest or directly from file path."""
    p = Path(identifier)
    if p.exists() and p.is_file():
        return ScenarioConfig.load(p)

    if SCENARIO_MANIFEST_PATH.exists():
        manifest = json.loads(SCENARIO_MANIFEST_PATH.read_text(encoding="utf-8"))
        if identifier in manifest.get("scenarios", {}):
            rel_file = manifest["scenarios"][identifier]["file"]
            scenario_path = Path("research") / rel_file
            if scenario_path.exists():
                return ScenarioConfig.load(scenario_path)

    # Search in subdirectories
    for split in ["train", "validation", "test"]:
        cand = Path("research/scenarios") / split / f"{identifier}.yaml"
        if cand.exists():
            return ScenarioConfig.load(cand)

    raise FileNotFoundError(f"Could not locate scenario '{identifier}'.")


def run_benchmark_suite(
    scenario_ids: List[str],
    controller_names: List[str],
    seeds: List[int],
    results_dir: Path = RESULTS_DIR,
    record_trajectory: bool = True,
    fault_injector: Optional[Any] = None,
) -> List[ExperimentResult]:
    """
    Execute paired CRN benchmark runs across all (Scenario, Controller, Seed) tuples.
    """
    runner = ExperimentRunner()
    results: List[ExperimentResult] = []

    logger.info(
        "Starting Benchmark Suite: %d scenarios, %d controllers, %d seeds (%d total runs)",
        len(scenario_ids), len(controller_names), len(seeds),
        len(scenario_ids) * len(controller_names) * len(seeds)
    )

    for sc_id in scenario_ids:
        scenario = load_scenario(sc_id)
        logger.info("=== Running Scenario: %s (%s, hash=%s) ===", scenario.name, scenario.scenario_id, scenario.scenario_hash)

        for seed in seeds:
            logger.info("--- CRN Seed %d ---", seed)
            for c_name in controller_names:
                ctrl = get_controller(c_name)
                logger.info("Executing Controller: %s", ctrl.name)

                res = runner.run(
                    controller=ctrl,
                    scenario=scenario,
                    seed=seed,
                    record_trajectory=record_trajectory,
                    fault_injector=fault_injector,
                )
                bundle_path = res.save_bundle(results_dir)
                results.append(res)
                logger.info(
                    "[%s | %s | seed %d] AvgDelay=%.2fs | P95=%.2fs | QArea=%.1f | Passed=%d | Starv=%d -> %s",
                    scenario.scenario_id, ctrl.name, seed,
                    res.avg_delay, res.p95_delay, res.queue_area, res.total_vehicles_passed, res.starvation_count,
                    bundle_path.name
                )

    return results


def export_summary_table(results: List[ExperimentResult], out_path: Path) -> None:
    """Export summary metrics table across all runs to CSV and JSON."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary_data = []

    for r in results:
        summary_data.append({
            "experiment_id": r.experiment_id,
            "scenario_id": r.scenario_id,
            "scenario_hash": r.scenario_hash,
            "controller": r.controller_name,
            "seed": r.seed,
            "avg_delay_s": r.avg_delay,
            "median_delay_s": r.median_delay,
            "p95_delay_s": r.p95_delay,
            "std_delay_s": r.std_delay,
            "queue_area_veh_s": r.queue_area,
            "max_queue_veh": r.max_queue,
            "passed_veh": r.total_vehicles_passed,
            "total_arrivals": r.total_arrivals,
            "service_rate": r.service_rate,
            "starvation_count": r.starvation_count,
            "watchdog_override_count": r.watchdog_override_count,
            "watchdog_override_rate": r.watchdog_override_rate,
            "wall_clock_s": r.elapsed_wall_seconds,
            "git_commit": r.git_commit,
        })

    csv_path = out_path.with_suffix(".csv")
    if summary_data:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(summary_data[0].keys()))
            writer.writeheader()
            writer.writerows(summary_data)

    json_path = out_path.with_suffix(".json")
    json_path.write_text(json.dumps(summary_data, indent=2), encoding="utf-8")
    logger.info("Exported benchmark suite summary: %s, %s", csv_path, json_path)


def print_comparison_table(results: List[ExperimentResult]) -> None:
    """Print clean comparison console table grouped by controller."""
    print("\n" + "=" * 105)
    print(f"{'Controller':<15} | {'Scenario':<24} | {'Seed':<5} | {'AvgDelay(s)':<11} | {'P95(s)':<8} | {'Q-Area':<8} | {'Passed':<6} | {'Starv':<5}")
    print("-" * 105)
    for r in results:
        print(f"{r.controller_name:<15} | {r.scenario_id:<24} | {r.seed:<5} | {r.avg_delay:<11.2f} | {r.p95_delay:<8.2f} | {r.queue_area:<8.1f} | {r.total_vehicles_passed:<6} | {r.starvation_count:<5}")
    print("=" * 105 + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="FlowSync Headless Research Benchmark Suite Runner")
    parser.add_argument("--suite", type=str, default="", help="Preset suite name: smoke, baselines, validation, test_clean, test_stress")
    parser.add_argument("--scenario", type=str, default="", help="Specific scenario ID or YAML file path")
    parser.add_argument("--controllers", type=str, default="fixed,greedy,max_pressure,d3qn", help="Comma-separated controller names")
    parser.add_argument("--seeds", type=str, default="42,1337,2026", help="Comma-separated seeds or range (e.g. 42,1337,2026 or 1000:1005)")
    parser.add_argument("--results-dir", type=str, default="results", help="Directory for immutable experiment output")
    parser.add_argument("--no-trajectory", action="store_true", help="Omit granular step trajectory logging to save disk space")
    parser.add_argument("--export-summary", type=str, default="results/suite_summary", help="Base filename for exported summary CSV/JSON")

    args = parser.parse_args()

    # Determine scenario list
    scenarios: List[str] = []
    if args.scenario:
        scenarios = [args.scenario]
    elif args.suite:
        if args.suite not in DEFAULT_SUITES:
            logger.error("Unknown suite '%s'. Available: %s", args.suite, list(DEFAULT_SUITES.keys()))
            sys.exit(1)
        scenarios = DEFAULT_SUITES[args.suite]
    else:
        scenarios = ["train_mod_balanced_01"]

    controllers = [c.strip() for c in args.controllers.split(",") if c.strip()]
    seeds = parse_seeds(args.seeds)
    results_dir = Path(args.results_dir)

    results = run_benchmark_suite(
        scenario_ids=scenarios,
        controller_names=controllers,
        seeds=seeds,
        results_dir=results_dir,
        record_trajectory=not args.no_trajectory,
    )

    print_comparison_table(results)
    export_summary_table(results, Path(args.export_summary))


if __name__ == "__main__":
    main()
