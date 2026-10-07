"""
run_city_scalability.py — 2x2 City Network Multi-Intersection Scalability (Phase M / Task M1)
=============================================================================================
Evaluates whether single-intersection research findings survive at network scale (2x2 grid, 4 intersections).
Evaluates Fixed, Greedy, Max-Pressure, D3QN, and FlowSync-UQ under coordinated network traffic.
Measures:
- Network-wide average delay (s/veh)
- Total network queue accumulation
- Network throughput (veh/h)
- Intersection decision compute latency (ms)
- Spillback / coordination stability
"""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path
from typing import Any, Dict, List
import numpy as np

from server.app.controllers import get_controller, ControllerContext
from server.app.simulation.city_network import CityNetwork
from server.app.simulation.city_spawner import CitySpawner
from server.app.simulation.traffic_signal import SignalColor
from research.analysis.table_generator import TableGenerator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("city_scalability")


def run_city_network_experiment(
    controller_name: str,
    duration_steps: int = 600,  # 60s at 10 Hz
    dt: float = 0.1,
    seed: int = 101,
) -> Dict[str, Any]:
    """
    Executes a 2x2 network simulation controlled by the specified controller architecture.
    """
    network = CityNetwork()
    spawner = CitySpawner(lambda_rate=0.4)
    spawner.set_enabled(True)
    spawner.set_seed(seed)

    controllers = {
        iid: get_controller(controller_name)
        for iid in ["A", "B", "C", "D"]
    }
    for ctrl in controllers.values():
        ctrl.reset(seed=seed)

    total_decisions = 0
    decision_latencies_ms: List[float] = []
    network_queues: List[int] = []

    for step in range(duration_steps):
        # 1. Spawn traffic onto perimeter edges
        spawner.spawn(dt, network.intersections)

        # 2. Control decision step (at 1 Hz / every 10 ticks or when phase can switch)
        for iid, intersection in network.intersections.items():
            signal = intersection.signal
            # If green phase decision tick (1 Hz)
            if signal.color == SignalColor.GREEN and step % 10 == 0:
                obs = network.build_obs(iid)
                mask = network.get_valid_action_mask(iid)

                context = ControllerContext(
                    timestep=step,
                    current_phase=signal.current_phase,
                    time_in_phase=signal.time_in_phase,
                    color=signal.color.name,
                    valid_action_mask=mask,
                    starvation_times={
                        d: intersection.starvation_tracker.get(d, 0.0)
                        for d in ["north", "south", "east", "west"]
                    } if hasattr(intersection, "starvation_tracker") else None,
                )

                t0 = time.perf_counter()
                action = controllers[iid].act(obs, context)
                lat_ms = (time.perf_counter() - t0) * 1000.0
                decision_latencies_ms.append(lat_ms)
                total_decisions += 1

                if signal.can_switch_phase and action != signal.current_phase and mask[action]:
                    signal.set_phase(action)

        # 3. Step network simulation physics
        network.tick(dt, mode="manual")

        # Telemetry
        q_sum = sum(
            sum(inter.get_movement_queues().values())
            for inter in network.intersections.values()
        )
        network_queues.append(q_sum)

    # Aggregate metrics across the network
    all_delays: List[float] = []
    total_passed = 0
    for inter in network.intersections.values():
        total_passed += inter.total_passed
        all_delays.extend(inter.completed_wait_times)

    mean_delay = float(np.mean(all_delays)) if all_delays else 0.0
    p95_delay = float(np.percentile(all_delays, 95)) if all_delays else 0.0
    mean_q = float(np.mean(network_queues))
    max_q = int(np.max(network_queues)) if network_queues else 0
    throughput = (total_passed / (duration_steps * dt)) * 3600.0
    mean_latency_ms = float(np.mean(decision_latencies_ms)) if decision_latencies_ms else 0.0
    p95_latency_ms = float(np.percentile(decision_latencies_ms, 95)) if decision_latencies_ms else 0.0

    return {
        "controller": controller_name,
        "seed": seed,
        "network_topology": "2x2_grid_4_intersections",
        "mean_delay": mean_delay,
        "p95_delay": p95_delay,
        "mean_network_queue": mean_q,
        "max_network_queue": max_q,
        "network_throughput": throughput,
        "total_vehicles_passed": total_passed,
        "mean_decision_latency_ms": mean_latency_ms,
        "p95_decision_latency_ms": p95_latency_ms,
        "total_decisions": total_decisions,
    }


def run_scalability_benchmark(
    controller_names: List[str] = ("fixed", "greedy", "max_pressure", "d3qn", "flowsync_uq"),
    seeds: List[int] = (101, 202),
    duration_steps: int = 600,
    results_dir: Path = Path("results/scalability"),
) -> List[Dict[str, Any]]:
    """
    Executes paired multi-seed benchmark across the 2x2 network.
    """
    results_dir.mkdir(parents=True, exist_ok=True)
    raw_runs: List[Dict[str, Any]] = []

    for c_name in controller_names:
        for seed in seeds:
            logger.info("Executing 2x2 City Network: Controller=%s, Seed=%d", c_name, seed)
            res = run_city_network_experiment(
                controller_name=c_name,
                duration_steps=duration_steps,
                seed=seed,
            )
            raw_runs.append(res)
            logger.info(
                "[City 2x2] %s (seed %d) -> MeanDelay=%.2fs, Q_avg=%.1f, Throughput=%.1f, Latency=%.2fms",
                c_name, seed, res["mean_delay"], res["mean_network_queue"], res["network_throughput"], res["mean_decision_latency_ms"]
            )

    # Summarize across seeds
    summary_records: List[Dict[str, Any]] = []
    for c_name in controller_names:
        matched = [r for r in raw_runs if r["controller"] == c_name]
        summary_records.append({
            "controller": c_name,
            "mean_delay": float(np.mean([r["mean_delay"] for r in matched])),
            "std_delay": float(np.std([r["mean_delay"] for r in matched])),
            "p95_delay": float(np.mean([r["p95_delay"] for r in matched])),
            "mean_network_queue": float(np.mean([r["mean_network_queue"] for r in matched])),
            "max_network_queue": int(np.max([r["max_network_queue"] for r in matched])),
            "network_throughput": float(np.mean([r["network_throughput"] for r in matched])),
            "mean_decision_latency_ms": float(np.mean([r["mean_decision_latency_ms"] for r in matched])),
            "p95_decision_latency_ms": float(np.mean([r["p95_decision_latency_ms"] for r in matched])),
        })

    summary_records.sort(key=lambda x: x["mean_delay"])

    # Export LaTeX table
    tex_path = results_dir / "table_city_2x2_scalability.tex"
    csv_path = results_dir / "table_city_2x2_scalability.csv"

    lines = [
        r"\begin{table*}[t]",
        r"\centering",
        r"\caption{Multi-Intersection Network Scalability Evaluation (2$\times$2 Grid, 4 Junctions)}",
        r"\label{tab:city_scalability}",
        r"\begin{tabular}{lcccccc}",
        r"\toprule",
        r"\textbf{Controller} & \textbf{Mean Delay (s)} & \textbf{P95 Delay (s)} & \textbf{Avg Net Queue} & \textbf{Throughput (veh/h)} & \textbf{Latency P95 (ms)} \\",
        r"\midrule",
    ]
    for r in summary_records:
        name = r["controller"]
        delay = f"{r['mean_delay']:.2f} $\\pm$ {r['std_delay']:.2f}"
        p95 = f"{r['p95_delay']:.2f}"
        q_avg = f"{r['mean_network_queue']:.1f}"
        tp = f"{r['network_throughput']:.1f}"
        lat = f"{r['p95_decision_latency_ms']:.2f}"
        if "flowsync_uq" in name.lower():
            lines.append(f"\\textbf{{{name}}} & \\textbf{{{delay}}} & \\textbf{{{p95}}} & \\textbf{{{q_avg}}} & \\textbf{{{tp}}} & \\textbf{{{lat}}} \\\\")
        else:
            lines.append(f"{name} & {delay} & {p95} & {q_avg} & {tp} & {lat} \\\\")
    lines.extend([
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table*}",
    ])
    tex_path.write_text("\n".join(lines), encoding="utf-8")
    TableGenerator.export_csv(summary_records, csv_path)

    logger.info("Saved 2x2 network scalability results: %s, %s", tex_path, csv_path)
    return summary_records


def main() -> None:
    parser = argparse.ArgumentParser(description="Run 2x2 city network scalability benchmark")
    parser.add_argument("--controllers", type=str, default="fixed,greedy,max_pressure,d3qn,flowsync_uq")
    parser.add_argument("--seeds", type=str, default="101,202")
    parser.add_argument("--steps", type=int, default=600)
    args = parser.parse_args()

    controllers = [c.strip() for c in args.controllers.split(",") if c.strip()]
    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]

    run_scalability_benchmark(controller_names=controllers, seeds=seeds, duration_steps=args.steps)


if __name__ == "__main__":
    main()
