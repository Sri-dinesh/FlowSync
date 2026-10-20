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
import math
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
        for key in ("miss_rate", "burst_miss_prob", "frame_drop_prob", "lane_misclass_prob"):
            if not 0 <= getattr(self.profile, key) <= 1:
                raise ValueError(f"{key} must be in [0, 1]")
        if self.profile.latency_ms < 0 or self.profile.false_positive_lambda < 0 or self.profile.jitter_std < 0:
            raise ValueError("Latency and noise magnitudes cannot be negative")
        self.seed = seed
        self._rng = np.random.default_rng(seed)

        # Latency ring buffer: dt=0.1s (100ms) per step
        self._latency_steps = max(0, int(math.ceil(self.profile.latency_ms / 100.0)))
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
        self.total_visible_vehicle_samples = 0
        self._packets = deque(maxlen=self._latency_steps + 1)
        self._last_packet = None

    def reset(self, seed: Optional[int] = None) -> None:
        """Reset fault generator state with optional seed refresh."""
        if seed is not None:
            self.seed = seed
        self._rng = np.random.default_rng(self.seed)
        self._obs_ring_buffer.clear()
        self._in_burst = False
        self._burst_steps_remaining = 0
        self._last_emitted_obs = None
        self._packets.clear()
        self._last_packet = None
        self.total_queries = self.total_missed_detections = 0
        self.total_false_positives = self.total_stale_frames = self.total_burst_steps = 0
        self.total_visible_vehicle_samples = 0

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
        return self._corrupt_packet(clean_obs, step, context)

    def _corrupt_packet(self, clean_obs, step, context):
        """Corrupt vehicle counts, arrivals and outflow together; retain frame age.

        A missed detection is a Bernoulli trial per vehicle sample. Synthetic
        fault truth is retained only in audit counters, never sent as confidence.
        """
        self.total_queries += 1
        # Independent step streams prevent controller-dependent queue sizes from
        # moving the fault schedule for later frames.
        rng = np.random.default_rng(np.random.SeedSequence([self.seed or 0, step]))
        drop = rng.random() < self.profile.frame_drop_prob
        burst_start = rng.random() < self.profile.burst_miss_prob
        if self._burst_steps_remaining <= 0 and burst_start:
            self._burst_steps_remaining = self.profile.burst_miss_duration
        in_burst = self._burst_steps_remaining > 0
        self._burst_steps_remaining = max(0, self._burst_steps_remaining - 1)
        self.total_burst_steps += int(in_burst)

        obs = np.copy(clean_obs)
        clean_counts = np.rint(15.0 * np.arctanh(np.clip(obs[:12], 0, 0.999999))).astype(int)
        self.total_visible_vehicle_samples += int(clean_counts.sum())
        counts = rng.binomial(clean_counts, 1.0 - self.profile.miss_rate)
        if in_burst:
            for i, movement in enumerate(MOVEMENT_KEYS):
                if movement.split("_")[0] in self.profile.burst_approaches:
                    counts[i] = 0
        self.total_missed_detections += int((clean_counts - counts).sum())
        ghosts = rng.poisson(self.profile.false_positive_lambda / 12.0, size=12)
        self.total_false_positives += int(ghosts.sum())
        counts += ghosts
        if self.profile.jitter_std:
            counts = np.maximum(0, np.rint(counts + rng.normal(0, self.profile.jitter_std * 15, 12))).astype(int)
        if rng.random() < self.profile.lane_misclass_prob:
            pair = int(rng.choice([0, 3, 6, 9]))
            counts[pair], counts[pair + 1] = counts[pair + 1], counts[pair]
        obs[:12] = np.tanh(counts / 15.0)

        outgoing = {}
        arrivals = 0
        if context is not None:
            outgoing = {d: int(rng.binomial(int(n), 1.0 - self.profile.miss_rate))
                        for d, n in (context.outgoing_counts or {}).items()}
            arrivals = int(rng.binomial(int(context.extra_telemetry.get("spawned_this_step", 0)),
                                       1.0 - self.profile.miss_rate))
            if in_burst:
                for d in self.profile.burst_approaches:
                    outgoing[d] = 0
        packet = (step, obs, outgoing, arrivals)
        self._packets.append(packet)
        selected = self._packets[0]
        if drop and self._last_packet is not None:
            selected = self._last_packet
            self.total_stale_frames += 1
        repeated = self._last_packet is not None and selected[0] == self._last_packet[0]
        self._last_packet = selected
        if context is not None:
            context.outgoing_counts = dict(selected[2])
            context.extra_telemetry.update(
                observation_age_ms=(step - selected[0]) * 100.0,
                frame_dropped=bool(drop or repeated),
                spawned_this_step=0 if repeated else selected[3],
            )
        self._last_emitted_obs = np.copy(selected[1])
        return np.copy(selected[1])


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
                self.total_missed_detections / max(1, self.total_visible_vehicle_samples)
            ),
            "total_visible_vehicle_samples": self.total_visible_vehicle_samples,
            "fault_model": "vehicle_sample_binomial_v2",
            "requested_profile": self.profile.to_dict(),
            "modeled_latency_ms": self._latency_steps * 100,
        }
