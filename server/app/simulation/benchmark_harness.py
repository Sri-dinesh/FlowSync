"""
benchmark_harness.py — FlowSync RL Deterministic Evaluation Harness
======================================================================
Task 0.1: Establish complete determinism across simulation environments,
vehicle spawn sequences, and evaluation runs using synchronized Common
Random Numbers (CRN).

Usage:
    from server.app.simulation.benchmark_harness import DeterministicEvaluator
    evaluator = DeterministicEvaluator(agent=agent, mode="ai")
    results = evaluator.run(num_steps=3000, seed=42)
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import random
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Canonical evaluation seeds (Common Random Numbers)
CRN_SEEDS: List[int] = [42, 1337, 2026, 9999, 7]

# Standard benchmark durations
BENCHMARK_STEPS_SHORT = 600    # 60s at 10 Hz
BENCHMARK_STEPS_MEDIUM = 1200  # 120s at 10 Hz
BENCHMARK_STEPS_LONG = 3000    # 300s at 10 Hz

EVAL_SEED: int = 1337


def seed_everything(seed: int = EVAL_SEED) -> None:
    """
    Globally synchronize all random number generators for reproducible benchmarks.

    Locks: Python random, NumPy, PyTorch (CPU + CUDA), environment hash seed.
    Must be called before ANY intersection/spawner/agent instantiation.
    """
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)

    # Optional torch seeding — only if torch is available
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except ImportError:
        pass


@dataclass
class EpisodeMetrics:
    """Per-episode performance metrics for a single benchmark run."""
    mode: str
    seed: int
    num_steps: int
    avg_wait_time: float
    total_vehicles_passed: int
    total_reward: float
    watchdog_override_count: int
    watchdog_override_rate: float
    # E-01: Scenario hash for CRN pairing audit
    scenario_hash: str = ""
    # E-05 / E-06 / E-07: Extended evaluation metrics
    queue_area: float = 0.0
    median_delay: float = 0.0
    p95_delay: float = 0.0
    std_delay: float = 0.0
    max_queue: int = 0
    reward_components: Dict[str, float] = field(default_factory=dict)
    # R-04: Detailed watchdog override audit log
    watchdog_overrides: List[Dict[str, Any]] = field(default_factory=list)
    elapsed_wall_seconds: float = 0.0
    # Starvation: number of times any direction waited > STARVATION_THRESHOLD steps
    starvation_count: int = 0


@dataclass
class BenchmarkResult:
    """Aggregated results across multiple seeds."""
    mode: str
    num_steps: int
    seeds: List[int]
    episodes: List[EpisodeMetrics] = field(default_factory=list)
    mean_avg_wait: float = 0.0
    std_avg_wait: float = 0.0
    mean_throughput: float = 0.0
    mean_override_rate: float = 0.0
    # E-01 / E-05 / E-06 / E-07: Extended aggregate metrics
    scenario_hash: str = ""
    mean_queue_area: float = 0.0
    mean_median_delay: float = 0.0
    mean_p95_delay: float = 0.0
    mean_max_queue: float = 0.0
    checkpoint_hash: str = ""
    environment_version: str = "v1.2"
    state_version: str = "v1_28d"
    reward_version: str = "v3_delay_anchored"
    hyperparams: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def compute_aggregates(self) -> None:
        """Compute mean/std from episode list."""
        if not self.episodes:
            return
        wait_times = [e.avg_wait_time for e in self.episodes]
        throughputs = [e.total_vehicles_passed for e in self.episodes]
        override_rates = [e.watchdog_override_rate for e in self.episodes]
        self.mean_avg_wait = float(np.mean(wait_times))
        self.std_avg_wait = float(np.std(wait_times))
        self.mean_throughput = float(np.mean(throughputs))
        self.mean_override_rate = float(np.mean(override_rates))
        self.mean_queue_area = float(np.mean([e.queue_area for e in self.episodes]))
        self.mean_median_delay = float(np.mean([e.median_delay for e in self.episodes]))
        self.mean_p95_delay = float(np.mean([e.p95_delay for e in self.episodes]))
        self.mean_max_queue = float(np.mean([e.max_queue for e in self.episodes]))
        if self.episodes:
            self.scenario_hash = self.episodes[0].scenario_hash

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)


class DeterministicEvaluator:
    """
    Runs locked-seed evaluation benchmarks for Fixed, Greedy, and AI control modes.

    Guarantees that:
    - All three modes see identical vehicle arrival sequences (same Poisson seed).
    - AI mode uses epsilon=0.0 (pure greedy inference).
    - Agent weights are snapshotted from the training agent before evaluation.
    - Full audit manifest is exportable as JSON.

    Args:
        agent: Optional DQNAgent. Required for mode="ai".
        mode: One of "fixed", "greedy", "ai".
        spawn_lambda: Vehicle arrival rate (vehicles/s).
        red_duration: All-red clearance duration in seconds.
    """

    def __init__(
        self,
        agent: Optional[Any] = None,
        mode: str = "ai",
        spawn_lambda: float = 0.5,
        red_duration: float = 3.0,
    ) -> None:
        self.agent = agent
        self.mode = mode.lower()
        self.spawn_lambda = spawn_lambda
        self.red_duration = red_duration

        if self.mode == "ai" and agent is None:
            raise ValueError("DeterministicEvaluator requires an agent for mode='ai'.")

    def _snapshot_agent_weights(self) -> None:
        """
        Freeze agent weights into eval mode. Prevents weight drift between
        training gradient steps and inference during benchmarks.
        """
        if self.agent is None:
            return
        self.agent.online_net.eval()
        logger.debug("Agent weights frozen to eval mode for benchmark.")

    def _restore_agent_training_mode(self) -> None:
        """Restore agent to training mode after benchmark."""
        if self.agent is None:
            return
        self.agent.online_net.train()

    def _compute_checkpoint_hash(self) -> str:
        """SHA-256 fingerprint of online network weights for audit trail."""
        if self.agent is None:
            return "no_agent"
        try:
            import io
            import torch
            buf = io.BytesIO()
            torch.save(self.agent.online_net.state_dict(), buf)
            return hashlib.sha256(buf.getvalue()).hexdigest()[:16]
        except Exception:
            return "hash_error"

    def _select_action(self, state: np.ndarray) -> int:
        """
        Select action per mode.
        - ai: epsilon=0.0 (pure greedy, no exploration)
        - greedy: max-queue pressure greedy heuristic
        - fixed: hold phase for fixed_duration, then cycle
        """
        if self.mode == "ai":
            return self.agent.select_action(state, epsilon=0.0)
        elif self.mode == "greedy":
            # Return -1; TrafficEnv greedy mode handles internally
            return -1
        else:
            return -1  # fixed: env handles internally

    def run(
        self,
        num_steps: int = BENCHMARK_STEPS_LONG,
        seed: int = EVAL_SEED,
    ) -> EpisodeMetrics:
        """
        Run a single deterministic evaluation episode.

        Args:
            num_steps: Number of simulation steps (dt=0.1s each).
            seed: Random seed for CRN.

        Returns:
            EpisodeMetrics with full telemetry.
        """
        # Import here to avoid circular imports at module load
        from .environment import TrafficEnv

        seed_everything(seed)
        self._snapshot_agent_weights()

        env = TrafficEnv()
        env.intersection.set_spawn_rate(self.spawn_lambda)
        state, _ = env.reset(seed=seed)

        # E-01: Compute immutable scenario hash for CRN verification
        scenario_spec = {
            "seed": seed,
            "num_steps": num_steps,
            "spawn_lambda": self.spawn_lambda,
            "red_duration": self.red_duration,
            "topology": "single_intersection",
        }
        scenario_hash = hashlib.sha256(
            json.dumps(scenario_spec, sort_keys=True).encode()
        ).hexdigest()[:16]

        total_reward = 0.0
        t_start = time.perf_counter()
        reward_components_accum: Dict[str, float] = {}
        queue_area: float = 0.0
        max_queue: int = 0
        watchdog_overrides: List[Dict[str, Any]] = []

        # Starvation tracking: count events where a direction is denied green
        # for >= STARVATION_THRESHOLD consecutive steps (~3 s at 10 Hz)
        STARVATION_THRESHOLD = 30
        _ALL_DIRS = ["north", "south", "east", "west"]
        _per_dir_no_green: Dict[str, int] = {d: 0 for d in _ALL_DIRS}
        starvation_events: int = 0

        vat_controller = None
        if self.mode in ("vat", "actuated"):
            from .vat_controller import VATController
            vat_controller = VATController(env.intersection)

        PHASE_DIRS = {0: ["north", "south"], 1: ["east", "west"], 2: ["north", "south"], 3: ["east", "west"]}
        PHASE_TURNS = {0: ["straight", "right"], 1: ["straight", "right"], 2: ["left"], 3: ["left"]}

        for step in range(num_steps):
            if self.mode == "ai":
                action = self._select_action(state)
            elif self.mode in ("fixed", "manual"):
                action = None
            elif self.mode in ("vat", "actuated"):
                action = vat_controller.select_action()
            elif self.mode == "greedy":
                signal = env.intersection.signal
                queues = env.intersection.get_movement_queues()
                phase_counts = {
                    ph: sum(
                        queues.get(f"{d}_{t}", 0)
                        for d in PHASE_DIRS[ph]
                        for t in PHASE_TURNS[ph]
                    )
                    for ph in range(4)
                }
                best_phase = max(phase_counts, key=lambda p: phase_counts[p])
                action = best_phase if signal.can_switch_phase else signal.current_phase
            else:
                action = None

            next_state, reward, terminated, truncated, info = env.step(action)
            if vat_controller is not None:
                vat_controller.update(
                    dt=0.1,
                    spawned_this_step=max(0, getattr(env.intersection, "_spawned_this_interval", 0)),
                )
            total_reward += reward

            # E-06: Accumulate queue area (integral of queue length over dt=0.1s)
            step_q = env.intersection.get_total_waiting()
            queue_area += step_q * 0.1
            if step_q > max_queue:
                max_queue = step_q

            # Starvation tracking: which directions got green this step?
            active_phase = env.intersection.signal.current_phase
            green_dirs = PHASE_DIRS.get(active_phase, [])
            for _d in _ALL_DIRS:
                if _d not in green_dirs:
                    _per_dir_no_green[_d] += 1
                    if _per_dir_no_green[_d] >= STARVATION_THRESHOLD:
                        starvation_events += 1
                        _per_dir_no_green[_d] = 0  # reset counter after event
                else:
                    _per_dir_no_green[_d] = 0

            # R-04: Log watchdog override details (requested vs executed action, reason)
            if info.get("was_overridden"):
                watchdog_overrides.append({
                    "step": step,
                    "proposed_action": info.get("proposed_action"),
                    "executed_action": info.get("executed_action"),
                    "reason": info.get("override_reason", "watchdog_safety"),
                })

            # Accumulate reward components if available
            for k, v in info.get("reward_components", {}).items():
                reward_components_accum[k] = reward_components_accum.get(k, 0.0) + v

            state = next_state
            if terminated or truncated:
                break

        elapsed = time.perf_counter() - t_start

        avg_wait = env.intersection.get_avg_wait_time()
        total_passed = env.intersection.total_passed
        watchdog_count = getattr(env, "watchdog_override_count", 0)
        total_decisions = max(getattr(env, "total_decision_steps", 1), 1)
        override_rate = (watchdog_count / total_decisions) * 100.0

        # E-07: Delay distribution statistics (median, p95, std)
        all_delays: List[float] = []
        if hasattr(env, "passed_vehicle_waits"):
            all_delays.extend(env.passed_vehicle_waits)
        for queue in env.intersection.lanes.values():
            for v in queue:
                if v.wait_time > 0:
                    all_delays.append(v.wait_time)

        if all_delays:
            median_delay = float(np.median(all_delays))
            p95_delay = float(np.percentile(all_delays, 95))
            std_delay = float(np.std(all_delays))
        else:
            median_delay = avg_wait
            p95_delay = avg_wait
            std_delay = 0.0

        self._restore_agent_training_mode()

        return EpisodeMetrics(
            mode=self.mode,
            seed=seed,
            num_steps=num_steps,
            avg_wait_time=avg_wait,
            total_vehicles_passed=total_passed,
            total_reward=total_reward,
            watchdog_override_count=watchdog_count,
            watchdog_override_rate=override_rate,
            scenario_hash=scenario_hash,
            queue_area=round(queue_area, 2),
            median_delay=round(median_delay, 2),
            p95_delay=round(p95_delay, 2),
            std_delay=round(std_delay, 2),
            max_queue=max_queue,
            reward_components=reward_components_accum,
            watchdog_overrides=watchdog_overrides,
            elapsed_wall_seconds=elapsed,
            starvation_count=starvation_events,
        )

    def run_multi_seed(
        self,
        num_steps: int = BENCHMARK_STEPS_LONG,
        seeds: Optional[List[int]] = None,
    ) -> BenchmarkResult:
        """
        Run evaluation across multiple CRN seeds, aggregate metrics.

        Args:
            num_steps: Steps per seed run.
            seeds: List of seeds. Defaults to CRN_SEEDS.

        Returns:
            BenchmarkResult with mean/std across all seeds.
        """
        seeds = seeds or CRN_SEEDS
        result = BenchmarkResult(
            mode=self.mode,
            num_steps=num_steps,
            seeds=seeds,
            checkpoint_hash=self._compute_checkpoint_hash(),
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        for seed in seeds:
            logger.info(
                "Evaluating mode=%s seed=%d steps=%d ...", self.mode, seed, num_steps
            )
            metrics = self.run(num_steps=num_steps, seed=seed)
            result.episodes.append(metrics)
            logger.info(
                "  avg_wait=%.2fs throughput=%d override_rate=%.1f%%",
                metrics.avg_wait_time,
                metrics.total_vehicles_passed,
                metrics.watchdog_override_rate,
            )

        result.compute_aggregates()
        logger.info(
            "Benchmark [%s]: mean_wait=%.2f±%.2fs mean_throughput=%.0f",
            self.mode,
            result.mean_avg_wait,
            result.std_avg_wait,
            result.mean_throughput,
        )
        return result

    def compare_all_modes(
        self,
        agent: Any,
        num_steps: int = BENCHMARK_STEPS_LONG,
        seeds: Optional[List[int]] = None,
    ) -> Dict[str, BenchmarkResult]:
        """
        Run all three modes (fixed, greedy, ai) with identical seeds and summarize.

        Args:
            agent: DQNAgent for AI mode.
            num_steps: Steps per evaluation.
            seeds: CRN seeds.

        Returns:
            Dict mapping mode -> BenchmarkResult.
        """
        seeds = seeds or CRN_SEEDS
        results: Dict[str, BenchmarkResult] = {}

        for mode in ("fixed", "greedy", "ai"):
            eval_agent = agent if mode == "ai" else None
            evaluator = DeterministicEvaluator(
                agent=eval_agent,
                mode=mode,
                spawn_lambda=self.spawn_lambda,
                red_duration=self.red_duration,
            )
            results[mode] = evaluator.run_multi_seed(num_steps=num_steps, seeds=seeds)

        return results


def print_comparison_table(results: Dict[str, "BenchmarkResult"]) -> str:
    """Format benchmark results as a Markdown table for console/logging output."""
    header = "| Mode   | Mean Wait (s) | Std  | p95 Wait (s) | Queue Area | Throughput | Override Rate |\n"
    header += "|--------|--------------|------|--------------|------------|-----------|---------------|\n"
    rows = []
    for mode, result in results.items():
        rows.append(
            f"| {mode:<6} | {result.mean_avg_wait:>12.2f} | {result.std_avg_wait:>4.2f} "
            f"| {result.mean_p95_delay:>12.2f} | {result.mean_queue_area:>10.1f} "
            f"| {result.mean_throughput:>9.0f} | {result.mean_override_rate:>12.1f}% |"
        )
    table = header + "\n".join(rows)
    logger.info("\nBenchmark Comparison:\n%s", table)
    return table
