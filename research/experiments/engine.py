"""
engine.py — FlowSync Research Experiment Execution Engine
===========================================================
Executes reproducible, deterministic traffic simulation experiments
under synchronized Common Random Numbers (CRN).

Guarantees:
1. Controller-Environment state isolation: No simulator oracle leakage.
2. Full controller independence: Controllers implement BaseController.
3. Common Random Numbers (CRN): Paired controllers see identical vehicle arrival schedules.
4. Immutable result bundling: Generates auditable result directories.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

# Ensure repository root and server/ are on sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent
_SERVER = _ROOT / "server"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_SERVER) not in sys.path:
    sys.path.insert(0, str(_SERVER))

from server.app.controllers.base import BaseController, ControllerContext
from server.app.simulation.environment import TrafficEnv
from server.app.simulation.benchmark_harness import seed_everything
from server.app.simulation.spawner import TrafficProfile
from research.scenarios.scenario_schema import ScenarioConfig

logger = logging.getLogger(__name__)


@dataclass
class ExperimentResult:
    """Immutable outcome record of a single benchmark run."""
    experiment_id: str
    scenario_id: str
    scenario_hash: str
    controller_name: str
    seed: int
    num_steps: int
    avg_delay: float
    median_delay: float
    p95_delay: float
    std_delay: float
    queue_area: float
    max_queue: int
    total_vehicles_passed: int
    total_arrivals: int
    service_rate: float
    starvation_count: int
    watchdog_override_count: int
    watchdog_override_rate: float
    total_reward: float
    elapsed_wall_seconds: float
    controller_capabilities: Dict[str, Any]
    git_commit: str = ""
    timestamp: str = ""
    checkpoint_hash: str = ""
    trajectory: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self, include_trajectory: bool = True) -> Dict[str, Any]:
        data = asdict(self)
        if not include_trajectory:
            data.pop("trajectory", None)
        return data

    def save_bundle(self, base_dir: Path | str) -> Path:
        """Save immutable experiment artifact bundle to disk."""
        target_dir = Path(base_dir) / self.experiment_id
        target_dir.mkdir(parents=True, exist_ok=True)

        # 1. metadata.json
        metadata = {
            "experiment_id": self.experiment_id,
            "scenario_id": self.scenario_id,
            "scenario_hash": self.scenario_hash,
            "controller_name": self.controller_name,
            "seed": self.seed,
            "git_commit": self.git_commit,
            "timestamp": self.timestamp,
            "checkpoint_hash": self.checkpoint_hash,
            "controller_capabilities": self.controller_capabilities,
        }
        (target_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        # 2. metrics.json
        metrics = {
            "avg_delay": self.avg_delay,
            "median_delay": self.median_delay,
            "p95_delay": self.p95_delay,
            "std_delay": self.std_delay,
            "queue_area": self.queue_area,
            "max_queue": self.max_queue,
            "total_vehicles_passed": self.total_vehicles_passed,
            "total_arrivals": self.total_arrivals,
            "service_rate": self.service_rate,
            "starvation_count": self.starvation_count,
            "watchdog_override_count": self.watchdog_override_count,
            "watchdog_override_rate": self.watchdog_override_rate,
            "total_reward": self.total_reward,
            "elapsed_wall_seconds": self.elapsed_wall_seconds,
        }
        (target_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

        # 3. Provenance text tags
        (target_dir / "git_commit.txt").write_text(self.git_commit, encoding="utf-8")
        (target_dir / "scenario_hash.txt").write_text(self.scenario_hash, encoding="utf-8")
        (target_dir / "seed.txt").write_text(str(self.seed), encoding="utf-8")
        if self.checkpoint_hash:
            (target_dir / "model_hash.txt").write_text(self.checkpoint_hash, encoding="utf-8")

        # 4. events.jsonl
        with open(target_dir / "events.jsonl", "w", encoding="utf-8") as f:
            for ev in self.events:
                f.write(json.dumps(ev) + "\n")

        # 5. trajectory.jsonl
        with open(target_dir / "trajectory.jsonl", "w", encoding="utf-8") as f:
            for pt in self.trajectory:
                f.write(json.dumps(pt) + "\n")

        return target_dir


class ExperimentRunner:
    """
    Executes a single (Controller, Scenario, Seed) trial in headless mode.
    """

    @staticmethod
    def get_git_commit() -> str:
        try:
            return subprocess.check_output(
                ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
            ).decode("ascii").strip()
        except Exception:
            return "unknown_commit"

    def run(
        self,
        controller: BaseController,
        scenario: ScenarioConfig,
        seed: int,
        record_trajectory: bool = True,
        fault_injector: Optional[Any] = None,
    ) -> ExperimentResult:
        """
        Execute deterministic simulation run.
        """
        t_start = time.perf_counter()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        git_commit = self.get_git_commit()

        # Generate unique deterministic experiment ID
        exp_id_raw = f"{scenario.scenario_id}_{controller.name}_seed{seed}_{timestamp}"
        exp_hash = hashlib.sha256(exp_id_raw.encode()).hexdigest()[:8]
        experiment_id = f"exp_{scenario.scenario_id}_{controller.name}_s{seed}_{exp_hash}"

        # 1. Global seed lock (CRN synchronization)
        seed_everything(seed)

        # 2. Reset controller internal state
        controller.reset(seed=seed)

        # 3. Instantiate and configure simulation environment
        num_steps = scenario.duration_steps
        env = TrafficEnv(max_steps=num_steps, red_duration=scenario.red_duration)

        # Build traffic profile from scenario demand profile
        dp = scenario.demand_profile
        profile = TrafficProfile(
            id=scenario.scenario_id,
            name=scenario.name,
            description=scenario.description,
            directional_weights=dp.directional_weights,
            turn_probs=[
                dp.turn_ratios["north"]["straight"],
                dp.turn_ratios["north"]["left"],
                dp.turn_ratios["north"]["right"],
            ],
            base_lambda=dp.base_lambda,
            lambda_multiplier=1.0,
        )
        env.set_traffic_profile(profile)

        # Environment reset with seed
        obs, _ = env.reset(seed=seed)

        # Telemetry accumulators
        total_reward = 0.0
        queue_area = 0.0
        max_queue = 0
        starvation_count = 0
        STARVATION_THRESHOLD = 450  # 45s at 10 Hz
        phase_unserved_steps = {0: 0, 1: 0, 2: 0, 3: 0}

        trajectory: List[Dict[str, Any]] = []
        events: List[Dict[str, Any]] = []

        PHASE_DIRS = {0: ["north", "south"], 1: ["east", "west"], 2: ["north", "south"], 3: ["east", "west"]}
        PHASE_TURNS = {0: ["straight"], 1: ["straight"], 2: ["left"], 3: ["left"]}

        # Step loop
        for step in range(num_steps):
            # Dynamic burst events from scenario
            current_lambda = dp.base_lambda
            for burst in dp.burst_events:
                if burst.get("start_step", 0) <= step <= burst.get("end_step", 0):
                    current_lambda *= burst.get("multiplier", 1.0)
            env.intersection.set_spawn_rate(current_lambda)

            # Build ControllerContext
            signal = env.intersection.signal
            queues = env.intersection.get_movement_queues()
            valid_mask = env.get_valid_action_mask()

            # Estimate outgoing counts
            outgoing_counts = {
                "north": sum(1 for v in env.intersection.lanes.get("north_straight", []) if v.position > 0.42),
                "south": sum(1 for v in env.intersection.lanes.get("south_straight", []) if v.position > 0.42),
                "east":  sum(1 for v in env.intersection.lanes.get("east_straight", []) if v.position > 0.42),
                "west":  sum(1 for v in env.intersection.lanes.get("west_straight", []) if v.position > 0.42),
            }

            ctx = ControllerContext(
                timestep=step,
                dt=0.1,
                current_phase=signal.current_phase,
                time_in_phase=signal.time_in_phase,
                color=signal.color.name,
                can_switch_phase=signal.can_switch_phase,
                is_decision_step=env.is_decision_step,
                valid_action_mask=valid_mask,
                movement_queues=queues,
                outgoing_counts=outgoing_counts,
                starvation_times=signal.starvation_timer.copy(),
                extra_telemetry={"spawned_this_step": max(0, getattr(env.intersection, "_generated_last_tick", 0))},
            )

            # Observation conditioning (e.g. fault injector if present)
            policy_obs = obs
            if fault_injector is not None:
                policy_obs = fault_injector.corrupt_observation(obs, step=step, context=ctx)

            # Controller action selection
            action = controller.act(policy_obs, ctx)

            # Environment step
            next_obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward

            # Accumulate queue area
            step_q = env.intersection.get_total_waiting()
            queue_area += step_q * 0.1
            if step_q > max_queue:
                max_queue = step_q

            # Track starvation
            for phase in range(4):
                demand = sum(
                    queues.get(f"{d}_{t}", 0)
                    for d in PHASE_DIRS[phase]
                    for t in PHASE_TURNS[phase]
                )
                is_served = signal.color.name == "GREEN" and signal.current_phase == phase
                if demand > 0 and not is_served:
                    phase_unserved_steps[phase] += 1
                    if phase_unserved_steps[phase] >= STARVATION_THRESHOLD:
                        starvation_count += 1
                        phase_unserved_steps[phase] = 0
                        events.append({
                            "type": "starvation_threshold_reached",
                            "step": step,
                            "phase": phase,
                            "wait_seconds": 45.0,
                        })
                else:
                    phase_unserved_steps[phase] = 0

            # Record override events
            if info.get("was_overridden"):
                events.append({
                    "type": "watchdog_override",
                    "step": step,
                    "proposed_action": info.get("proposed_action"),
                    "executed_action": info.get("executed_action"),
                    "reason": info.get("override_reason"),
                })

            # Record trajectory frame
            if record_trajectory and (step % 5 == 0 or step == num_steps - 1):
                trajectory.append({
                    "step": step,
                    "phase": signal.current_phase,
                    "color": signal.color.name,
                    "action": action,
                    "executed_action": info.get("executed_action"),
                    "total_waiting": step_q,
                    "reward": round(reward, 4),
                })

            obs = next_obs
            if terminated or truncated:
                break

        elapsed = time.perf_counter() - t_start

        # Calculate final delay statistics
        all_delays: List[float] = []
        if hasattr(env, "passed_vehicle_waits"):
            all_delays.extend(env.passed_vehicle_waits)
        for queue in env.intersection.lanes.values():
            for v in queue:
                if v.wait_time > 0:
                    all_delays.append(v.wait_time)
        all_delays.extend(env.intersection.spawner.get_backlog_waits())

        avg_delay = float(env.intersection.get_avg_wait_time())
        if all_delays:
            median_delay = float(np.median(all_delays))
            p95_delay = float(np.percentile(all_delays, 95))
            std_delay = float(np.std(all_delays))
        else:
            median_delay = avg_delay
            p95_delay = avg_delay
            std_delay = 0.0

        total_passed = int(env.intersection.total_passed)
        total_arrivals = int(env.intersection.spawner.total_generated)
        service_rate = float(total_passed / max(total_arrivals, 1))
        watchdog_count = int(getattr(env, "watchdog_override_count", 0))
        total_decisions = max(getattr(env, "total_decision_steps", 1), 1)
        override_rate = float((watchdog_count / total_decisions) * 100.0)

        diag = controller.get_diagnostics()
        checkpoint_hash = str(diag.get("checkpoint_hash", ""))

        return ExperimentResult(
            experiment_id=experiment_id,
            scenario_id=scenario.scenario_id,
            scenario_hash=scenario.scenario_hash,
            controller_name=controller.name,
            seed=seed,
            num_steps=num_steps,
            avg_delay=round(avg_delay, 3),
            median_delay=round(median_delay, 3),
            p95_delay=round(p95_delay, 3),
            std_delay=round(std_delay, 3),
            queue_area=round(queue_area, 2),
            max_queue=max_queue,
            total_vehicles_passed=total_passed,
            total_arrivals=total_arrivals,
            service_rate=round(service_rate, 4),
            starvation_count=starvation_count,
            watchdog_override_count=watchdog_count,
            watchdog_override_rate=round(override_rate, 2),
            total_reward=round(total_reward, 3),
            elapsed_wall_seconds=round(elapsed, 3),
            controller_capabilities=controller.get_capabilities().to_dict(),
            git_commit=git_commit,
            timestamp=timestamp,
            checkpoint_hash=checkpoint_hash,
            trajectory=trajectory,
            events=events,
        )
