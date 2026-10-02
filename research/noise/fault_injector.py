"""
fault_injector.py — Seeded Perception Noise and Fault Injection Engine
======================================================================
Task 1A.9 & Task E2: Injects realistic, reproducible perception disturbances
between the environment observation and the controller policy.

Supported Fault Models:
1. Bernoulli Missed Detections: Independent vehicle omission probability p_miss.
2. Burst / Correlated Occlusion: Prolonged line-of-sight loss on specific approaches.
3. False Positives: Additive Poisson phantom vehicle detections.
4. Coordinate / Bounding-Box Jitter: Gaussian perturbation on queue counts.
5. Observation Latency: Delay queue states by tau_ms (100ms - 1000ms) via ring buffer.
6. Stale Frame Drops: Repeated freeze of previous observation for K steps.
7. Lane Misclassification: Shuffling vehicles into adjacent turning bays.
8. Combined Stress Profile: Multi-fault compounding.

Guarantees:
- Noise uses an independent random seed (CRN traffic schedule is unaffected).
- Ground-truth simulator state remains pristine.
- Requested vs realized fault rates are tracked and logged.
"""
from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np

from server.app.controllers.base import ControllerContext
from server.app.simulation.traffic_math import MOVEMENT_KEYS


@dataclass
class FaultProfile:
    """Configuration for reproducible perception fault injection."""
    name: str = "clean"
    miss_rate: float = 0.0              # Bernoulli miss probability per movement [0.0, 0.5]
    burst_miss_prob: float = 0.0        # Probability of entering a multi-step occlusion burst
    burst_miss_duration: int = 50       # Steps of burst occlusion (50 steps = 5.0s)
    burst_approaches: List[str] = field(default_factory=lambda: ["north", "south"])
    false_positive_lambda: float = 0.0  # Poisson mean for ghost vehicles
    jitter_std: float = 0.0             # Gaussian noise std on queues
    latency_ms: int = 0                 # Delay in milliseconds (multiples of 100ms)
    frame_drop_prob: float = 0.0        # Probability of holding stale previous frame
    lane_misclass_prob: float = 0.0     # Probability of swapping adjacent lane queues

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Canonical preset disturbance profiles
FAULT_PRESETS: Dict[str, FaultProfile] = {
    "clean": FaultProfile(name="clean"),
    "miss_05": FaultProfile(name="miss_05", miss_rate=0.05),
    "miss_10": FaultProfile(name="miss_10", miss_rate=0.10),
    "miss_20": FaultProfile(name="miss_20", miss_rate=0.20),
    "miss_30": FaultProfile(name="miss_30", miss_rate=0.30),
    "miss_40": FaultProfile(name="miss_40", miss_rate=0.40),
    "burst_occlusion": FaultProfile(
        name="burst_occlusion",
        burst_miss_prob=0.05,
        burst_miss_duration=40,
        burst_approaches=["north", "south"],
    ),
    "false_positives": FaultProfile(name="false_positives", false_positive_lambda=0.4),
    "latency_250ms": FaultProfile(name="latency_250ms", latency_ms=250),
    "latency_500ms": FaultProfile(name="latency_500ms", latency_ms=500),
    "latency_1000ms": FaultProfile(name="latency_1000ms", latency_ms=1000),
    "combined_moderate": FaultProfile(
        name="combined_moderate",
        miss_rate=0.15,
        latency_ms=200,
        false_positive_lambda=0.2,
        jitter_std=0.05,
    ),
    "combined_severe": FaultProfile(
        name="combined_severe",
        miss_rate=0.30,
        latency_ms=500,
        burst_miss_prob=0.08,
        burst_miss_duration=50,
        false_positive_lambda=0.4,
        frame_drop_prob=0.10,
    ),
}


class PerceptionFaultInjector:
    """
    Applies controlled, reproducible corruption to observation vectors.
    """

    def __init__(self, profile: Optional[FaultProfile] = None, seed: Optional[int] = None) -> None:
        self.profile = profile or FaultProfile()
        self.seed = seed
        self._rng = np.random.default_rng(seed)

        # Latency ring buffer: dt=0.1s (100ms) per step
        self._latency_steps = max(0, int(round(self.profile.latency_ms / 100.0)))
        self._obs_ring_buffer: deque[np.ndarray] = deque(maxlen=max(1, self._latency_steps + 1))

        # Burst occlusion state
        self._in_burst: bool = False
        self._burst_steps_remaining: int = 0
        self._last_emitted_obs: Optional[np.ndarray] = None

        # Telemetry auditing
        self.total_queries: int = 0
        self.total_missed_detections: int = 0
        self.total_false_positives: int = 0
        self.total_stale_frames: int = 0
        self.total_burst_steps: int = 0

    def reset(self, seed: Optional[int] = None) -> None:
        """Reset fault generator state with optional seed refresh."""
        if seed is not None:
            self.seed = seed
        self._rng = np.random.default_rng(self.seed)
        self._obs_ring_buffer.clear()
        self._in_burst = False
        self._burst_steps_remaining = 0
        self._last_emitted_obs = None

    def reset_seed(self, seed: int) -> None:
        """Alias for reset(seed)."""
        self.reset(seed)
        self.total_queries = 0
        self.total_missed_detections = 0
        self.total_false_positives = 0
        self.total_stale_frames = 0
        self.total_burst_steps = 0

    def corrupt_observation(
        self,
        clean_obs: np.ndarray,
        step: int = 0,
        context: Optional[ControllerContext] = None,
    ) -> np.ndarray:
        """
        Produce corrupted observation vector according to the active FaultProfile.
        Clean observation remains untouched.
        """
        self.total_queries += 1
        obs = np.copy(clean_obs)

        # 1. Stale Frame Drop
        if (
            self.profile.frame_drop_prob > 0.0
            and self._last_emitted_obs is not None
            and self._rng.random() < self.profile.frame_drop_prob
        ):
            self.total_stale_frames += 1
            return np.copy(self._last_emitted_obs)

        # 2. Burst Occlusion Handling
        if self._in_burst:
            self._burst_steps_remaining -= 1
            self.total_burst_steps += 1
            if self._burst_steps_remaining <= 0:
                self._in_burst = False
        elif (
            self.profile.burst_miss_prob > 0.0
            and self._rng.random() < self.profile.burst_miss_prob
        ):
            self._in_burst = True
            self._burst_steps_remaining = self.profile.burst_miss_duration
            self.total_burst_steps += 1

        # Dims 0-11: movement queues
        # Apply queue-level faults
        queues = np.copy(obs[:12])

        # (a) Bernoulli Missed Detections
        if self.profile.miss_rate > 0.0:
            for i in range(12):
                if queues[i] > 0 and self._rng.random() < self.profile.miss_rate:
                    # Scale down observed queue
                    loss_factor = self._rng.uniform(0.3, 0.9)
                    queues[i] = max(0.0, queues[i] * (1.0 - loss_factor))
                    self.total_missed_detections += 1

        # (b) Burst Occlusion on designated approaches
        if self._in_burst:
            for i, movement in enumerate(MOVEMENT_KEYS):
                dir_name = movement.split("_")[0]
                if dir_name in self.profile.burst_approaches:
                    # Approach is occluded: camera sees near-zero demand
                    queues[i] *= 0.05

        # (c) False Positives (Ghost Vehicles)
        if self.profile.false_positive_lambda > 0.0:
            fp_count = self._rng.poisson(self.profile.false_positive_lambda)
            if fp_count > 0:
                for _ in range(fp_count):
                    idx = self._rng.integers(0, 12)
                    ghost_addition = self._rng.uniform(0.08, 0.20)  # normalized ghost queue
                    queues[idx] = min(1.0, queues[idx] + ghost_addition)
                    self.total_false_positives += 1

        # (d) Bounding Box / Coordinate Jitter
        if self.profile.jitter_std > 0.0:
            noise = self._rng.normal(0.0, self.profile.jitter_std, size=12)
            queues = np.clip(queues + noise, 0.0, 1.0)

        # (e) Lane Misclassification (swap straight with left on same approach)
        if self.profile.lane_misclass_prob > 0.0 and self._rng.random() < self.profile.lane_misclass_prob:
            # Pair indices: (0, 1) for north, (3, 4) for south, (6, 7) for east, (9, 10) for west
            pair = self._rng.choice([0, 3, 6, 9])
            queues[pair], queues[pair + 1] = queues[pair + 1], queues[pair]

        obs[:12] = queues

        # 3. Observation Latency (Ring Buffer Delay)
        if self._latency_steps > 0:
            self._obs_ring_buffer.append(obs)
            # If buffer not full yet, return earliest available or zero-padded
            delayed_obs = self._obs_ring_buffer[0]
            emitted_obs = np.copy(delayed_obs)
        else:
            emitted_obs = obs

        self._last_emitted_obs = np.copy(emitted_obs)
        return emitted_obs

    def get_realized_diagnostics(self) -> Dict[str, Any]:
        """Audit statistics of realized corruption."""
        return {
            "profile_name": self.profile.name,
            "total_queries": self.total_queries,
            "total_missed_detections": self.total_missed_detections,
            "total_false_positives": self.total_false_positives,
            "total_stale_frames": self.total_stale_frames,
            "total_burst_steps": self.total_burst_steps,
            "realized_miss_rate": (
                self.total_missed_detections / max(1, self.total_queries * 12)
            ),
        }
