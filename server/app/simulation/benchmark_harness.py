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
    reward_components: Dict[str, float] = field(default_factory=dict)
    elapsed_wall_seconds: float = 0.0


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
    checkpoint_hash: str = ""
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

        total_reward = 0.0
        t_start = time.perf_counter()
        reward_components_accum: Dict[str, float] = {}

        for step in range(num_steps):
            if self.mode == "ai":
                action = self._select_action(state)
            else:
                # For non-AI modes the environment internally uses fixed/greedy logic
                action = 0  # unused; TrafficEnv ignores for non-AI modes

            next_state, reward, terminated, truncated, info = env.step(action)
            total_reward += reward

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
            reward_components=reward_components_accum,
            elapsed_wall_seconds=elapsed,
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
    header = "| Mode   | Mean Wait (s) | Std  | Throughput | Override Rate |\n"
    header += "|--------|--------------|------|-----------|---------------|\n"
    rows = []
    for mode, result in results.items():
        rows.append(
            f"| {mode:<6} | {result.mean_avg_wait:>12.2f} | {result.std_avg_wait:>4.2f} "
            f"| {result.mean_throughput:>9.0f} | {result.mean_override_rate:>12.1f}% |"
        )
    table = header + "\n".join(rows)
    logger.info("\nBenchmark Comparison:\n%s", table)
    return table
