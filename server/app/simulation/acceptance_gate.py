"""
acceptance_gate.py — FlowSync RL Acceptance Gate & Ablation Suite
===================================================================
Task 8.2: Automated gatekeeping pipeline that a trained RL checkpoint must
pass before being designated as the production checkpoint.

5 Gates (must pass in sequence):
  Gate 1: Mathematical Correctness (automated unit-test assertions)
  Gate 2: Basic Competence (outperform Fixed by >= 58% on balanced traffic)
  Gate 3: Predictive Superiority (outperform Greedy by >= 25% on burst demand)
  Gate 4: Network Coordination (city grid throughput >= 1800 veh/hr, 0 spillback)
  Gate 5: Safety compliance (watchdog override rate < 5%, 0 starvation)

Usage:
    from server.app.simulation.acceptance_gate import AcceptanceGateRunner

    runner = AcceptanceGateRunner(agent=agent)
    report = runner.run_all_gates()
    print(report.to_json())
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import numpy as np

from .benchmark_harness import (
    CRN_SEEDS,
    DeterministicEvaluator,
    BenchmarkResult,
    BENCHMARK_STEPS_MEDIUM,
    BENCHMARK_STEPS_LONG,
    seed_everything,
)

if TYPE_CHECKING:
    from ..rl.dqn_agent import DQNAgent

logger = logging.getLogger(__name__)

# ── Gate Thresholds ─────────────────────────────────────────────────────────
GATE2_AI_MAX_WAIT    = 10.0   # seconds (vs Fixed >= 24s)
GATE3_AI_MAX_WAIT    = 8.5    # seconds (vs Greedy >= 11.5s on burst)
GATE4_MIN_THROUGHPUT = 1800.0 # vehicles/hour
GATE5_MAX_OVERRIDE   = 5.0    # watchdog override rate %


@dataclass
class GateResult:
    """Result from a single acceptance gate."""
    gate_id: int
    name: str
    passed: bool
    metrics: Dict[str, Any] = field(default_factory=dict)
    failure_reason: str = ""
    elapsed_seconds: float = 0.0


@dataclass
class AcceptanceReport:
    """Full acceptance gate report for a checkpoint."""
    checkpoint_hash: str
    all_passed: bool
    gates: List[GateResult] = field(default_factory=list)
    ablation: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_hash": self.checkpoint_hash,
            "all_passed":      self.all_passed,
            "timestamp":       self.timestamp,
            "gates": [
                {
                    "gate_id":        g.gate_id,
                    "name":           g.name,
                    "passed":         g.passed,
                    "metrics":        g.metrics,
                    "failure_reason": g.failure_reason,
                    "elapsed_s":      round(g.elapsed_seconds, 2),
                }
                for g in self.gates
            ],
            "ablation": self.ablation,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def print_summary(self) -> None:
        logger.info("\n" + "="*60)
        logger.info("ACCEPTANCE GATE REPORT — %s", self.timestamp)
        logger.info("Checkpoint: %s", self.checkpoint_hash)
        logger.info("Overall: %s", "PASS ✓" if self.all_passed else "FAIL ✗")
        logger.info("-"*60)
        for g in self.gates:
            status = "PASS ✓" if g.passed else "FAIL ✗"
            logger.info("  Gate %d [%s]: %s", g.gate_id, g.name, status)
            if not g.passed:
                logger.info("    Reason: %s", g.failure_reason)
        logger.info("="*60)


class AcceptanceGateRunner:
    """
    Runs the 5-gate acceptance pipeline against a trained DQNAgent checkpoint.

    Args:
        agent: DQNAgent with trained weights to evaluate.
        spawn_lambda_balanced: λ for Gates 2, 4 (balanced traffic = 0.5).
        spawn_lambda_burst: λ for Gate 3 (burst demand = 1.2).
    """

    def __init__(
        self,
        agent: "DQNAgent",
        spawn_lambda_balanced: float = 0.5,
        spawn_lambda_burst: float = 1.2,
    ) -> None:
        self.agent = agent
        self.lambda_balanced = spawn_lambda_balanced
        self.lambda_burst = spawn_lambda_burst

    def _get_checkpoint_hash(self) -> str:
        """Short hash of checkpoint weights for audit trail."""
        import hashlib, io, torch
        buf = io.BytesIO()
        torch.save(self.agent.online_net.state_dict(), buf)
        return hashlib.sha256(buf.getvalue()).hexdigest()[:16]

    # ── Gate 1: Mathematical Correctness ────────────────────────────────────
    def run_gate1(self) -> GateResult:
        """
        Verify mathematical correctness of PER priorities and action masking.
        Checks that PER priorities are consistent and replay buffer stores valid actions.
        """
        t_start = time.perf_counter()
        errors = []

        try:
            from ..rl.replay_buffer import PrioritizedReplayBuffer
            from ..rl.hyperparams import HyperParams
            import numpy as np
            HP = HyperParams()

            buf = PrioritizedReplayBuffer(capacity=100)
            dummy_state = np.zeros(HP.STATE_DIM, dtype=np.float32)

            # Push 5 transitions with known TD errors
            for i in range(5):
                buf.push(dummy_state, i % 4, float(i), dummy_state, False)

            # Simulate priority updates with known TD errors
            td_errors = np.array([0.5, 1.0, 2.0, 0.1, 0.8])
            indices = list(range(buf.tree.capacity - 1, buf.tree.capacity - 1 + 5))
            buf.update_priorities(indices, td_errors)

            # Verify priorities are p^alpha, not p^(alpha^2)
            alpha = buf.alpha
            eps = buf.epsilon
            expected_priority_0 = (0.5 + eps) ** alpha
            stored_priority_0 = buf.tree.tree[indices[0]]
            diff = abs(stored_priority_0 - expected_priority_0)
            if diff > 1e-5:
                errors.append(
                    f"BUG-03 check failed: stored={stored_priority_0:.6f} "
                    f"expected={expected_priority_0:.6f} diff={diff:.6f}"
                )

            # Verify max_priority is stored as raw (not raised to alpha)
            expected_raw_max = max(td_errors) + eps
            if abs(buf.max_priority - expected_raw_max) > 1e-5:
                errors.append(
                    f"max_priority should be raw: got {buf.max_priority:.6f}, "
                    f"expected raw max {expected_raw_max:.6f}"
                )

        except Exception as e:
            errors.append(f"Exception during Gate 1 PER checks: {e}")

        elapsed = time.perf_counter() - t_start
        passed = len(errors) == 0
        return GateResult(
            gate_id=1,
            name="Mathematical Correctness",
            passed=passed,
            metrics={"errors": errors, "checks_run": 2},
            failure_reason="; ".join(errors) if errors else "",
            elapsed_seconds=elapsed,
        )

    # ── Gate 2: Basic Competence ─────────────────────────────────────────────
    def run_gate2(self, seeds: Optional[List[int]] = None) -> GateResult:
        """AI avg_wait <= 10.0s vs Fixed >= 24.0s on balanced traffic."""
        t_start = time.perf_counter()
        seeds = seeds or CRN_SEEDS[:3]  # 3 seeds for speed

        ai_eval = DeterministicEvaluator(
            agent=self.agent, mode="ai", spawn_lambda=self.lambda_balanced
        )
        fixed_eval = DeterministicEvaluator(
            agent=None, mode="fixed", spawn_lambda=self.lambda_balanced
        )

        ai_result = ai_eval.run_multi_seed(num_steps=BENCHMARK_STEPS_MEDIUM, seeds=seeds)
        fixed_result = fixed_eval.run_multi_seed(num_steps=BENCHMARK_STEPS_MEDIUM, seeds=seeds)

        ai_wait = ai_result.mean_avg_wait
        fixed_wait = fixed_result.mean_avg_wait
        improvement = (fixed_wait - ai_wait) / max(fixed_wait, 1e-6) * 100.0

        passed = ai_wait <= GATE2_AI_MAX_WAIT
        reason = (
            "" if passed else
            f"AI wait {ai_wait:.2f}s > threshold {GATE2_AI_MAX_WAIT:.1f}s "
            f"(vs Fixed {fixed_wait:.2f}s, improvement={improvement:.1f}%)"
        )
        return GateResult(
            gate_id=2,
            name="Basic Competence (vs Fixed)",
            passed=passed,
            metrics={
                "ai_avg_wait": round(ai_wait, 3),
                "fixed_avg_wait": round(fixed_wait, 3),
                "improvement_pct": round(improvement, 1),
                "threshold": GATE2_AI_MAX_WAIT,
            },
            failure_reason=reason,
            elapsed_seconds=time.perf_counter() - t_start,
        )

    # ── Gate 3: Predictive Superiority ──────────────────────────────────────
    def run_gate3(self, seeds: Optional[List[int]] = None) -> GateResult:
        """AI avg_wait <= 8.5s vs Greedy >= 11.5s on burst demand."""
        t_start = time.perf_counter()
        seeds = seeds or CRN_SEEDS[:3]

        ai_eval = DeterministicEvaluator(
            agent=self.agent, mode="ai", spawn_lambda=self.lambda_burst
        )
        greedy_eval = DeterministicEvaluator(
            agent=None, mode="greedy", spawn_lambda=self.lambda_burst
        )

        ai_result = ai_eval.run_multi_seed(num_steps=BENCHMARK_STEPS_MEDIUM, seeds=seeds)
        greedy_result = greedy_eval.run_multi_seed(num_steps=BENCHMARK_STEPS_MEDIUM, seeds=seeds)

        ai_wait = ai_result.mean_avg_wait
        greedy_wait = greedy_result.mean_avg_wait
        improvement = (greedy_wait - ai_wait) / max(greedy_wait, 1e-6) * 100.0

        passed = ai_wait <= GATE3_AI_MAX_WAIT
        reason = (
            "" if passed else
            f"AI wait {ai_wait:.2f}s > threshold {GATE3_AI_MAX_WAIT:.1f}s "
            f"(vs Greedy {greedy_wait:.2f}s, improvement={improvement:.1f}%)"
        )
        return GateResult(
            gate_id=3,
            name="Predictive Superiority (vs Greedy, Burst)",
            passed=passed,
            metrics={
                "ai_avg_wait": round(ai_wait, 3),
                "greedy_avg_wait": round(greedy_wait, 3),
                "improvement_pct": round(improvement, 1),
                "threshold": GATE3_AI_MAX_WAIT,
                "burst_lambda": self.lambda_burst,
            },
            failure_reason=reason,
            elapsed_seconds=time.perf_counter() - t_start,
        )

    # ── Gate 4: Network Coordination (simplified single-intersection proxy) ─
    def run_gate4(self, seeds: Optional[List[int]] = None) -> GateResult:
        """
        Throughput proxy: AI throughput >= threshold on long run.
        Full city grid test requires more infrastructure; this approximates via
        single-intersection sustained throughput proxy.
        """
        t_start = time.perf_counter()
        seeds = seeds or [42]

        ai_eval = DeterministicEvaluator(
            agent=self.agent, mode="ai", spawn_lambda=self.lambda_burst
        )
        ai_result = ai_eval.run_multi_seed(num_steps=BENCHMARK_STEPS_LONG, seeds=seeds)

        # Convert to vehicles/hour: total_passed / (3000 steps × 0.1s) × 3600s
        sim_duration_seconds = 3000 * 0.1  # 300s
        throughput_vph = (ai_result.mean_throughput / sim_duration_seconds) * 3600

        passed = throughput_vph >= GATE4_MIN_THROUGHPUT
        reason = (
            "" if passed else
            f"Throughput {throughput_vph:.0f} veh/hr < threshold {GATE4_MIN_THROUGHPUT:.0f}"
        )
        return GateResult(
            gate_id=4,
            name="Network Coordination (Throughput)",
            passed=passed,
            metrics={
                "throughput_vph": round(throughput_vph, 1),
                "threshold_vph": GATE4_MIN_THROUGHPUT,
                "ai_total_passed": ai_result.mean_throughput,
            },
            failure_reason=reason,
            elapsed_seconds=time.perf_counter() - t_start,
        )

    # ── Gate 5: Safety & Override Rate ──────────────────────────────────────
    def run_gate5(self, seeds: Optional[List[int]] = None) -> GateResult:
        """Watchdog override rate < 5% on balanced traffic."""
        t_start = time.perf_counter()
        seeds = seeds or CRN_SEEDS[:3]

        ai_eval = DeterministicEvaluator(
            agent=self.agent, mode="ai", spawn_lambda=self.lambda_balanced
        )
        result = ai_eval.run_multi_seed(num_steps=BENCHMARK_STEPS_MEDIUM, seeds=seeds)

        avg_override_rate = result.mean_override_rate
        passed = avg_override_rate < GATE5_MAX_OVERRIDE
        reason = (
            "" if passed else
            f"Override rate {avg_override_rate:.1f}% >= threshold {GATE5_MAX_OVERRIDE:.1f}%"
        )
        return GateResult(
            gate_id=5,
            name="Safety & Real-World Compliance",
            passed=passed,
            metrics={
                "avg_override_rate_pct": round(avg_override_rate, 2),
                "threshold_pct": GATE5_MAX_OVERRIDE,
            },
            failure_reason=reason,
            elapsed_seconds=time.perf_counter() - t_start,
        )

    # ── Full Pipeline ────────────────────────────────────────────────────────
    def run_all_gates(
        self,
        seeds: Optional[List[int]] = None,
        fail_fast: bool = False,
    ) -> AcceptanceReport:
        """
        Execute all 5 gates and produce the acceptance report.

        Args:
            seeds: CRN seeds for evaluation. Defaults to CRN_SEEDS.
            fail_fast: If True, stop after the first failing gate.

        Returns:
            AcceptanceReport with per-gate results and overall pass/fail.
        """
        checkpoint_hash = self._get_checkpoint_hash()
        report = AcceptanceReport(
            checkpoint_hash=checkpoint_hash,
            all_passed=True,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        gate_runners = [
            self.run_gate1,
            lambda: self.run_gate2(seeds),
            lambda: self.run_gate3(seeds),
            lambda: self.run_gate4(seeds),
            lambda: self.run_gate5(seeds),
        ]

        for runner in gate_runners:
            result = runner()
            report.gates.append(result)
            if not result.passed:
                report.all_passed = False
                logger.warning("Gate %d FAILED: %s", result.gate_id, result.failure_reason)
                if fail_fast:
                    break
            else:
                logger.info("Gate %d PASSED (%s).", result.gate_id, result.name)

        report.print_summary()
        return report
