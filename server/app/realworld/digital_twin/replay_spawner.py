"""
RealWorldSpawner — Drop-in replacement for simulation's TrafficSpawner.
Uses calibrated flow parameters from FlowCalibrator instead of fixed Poisson(lambda=0.8).
"""
from __future__ import annotations

import random
from typing import Dict, Optional

import numpy as np

from ..models.config import LANE_KEYS, VEHICLE_CLASSES, VEHICLE_QUEUE_WEIGHTS
from ..models.schemas import TrafficFlowParams


class RealWorldSpawner:
    """
    Drives the simulation with real-data-calibrated traffic flow parameters.

    MODE A — Calibrated Stochastic (for DQN training):
    Uses calibrated lambda per lane per time period (morning_peak, evening_peak, off_peak).
    Still stochastic (Poisson process), but with real arrival rates.

    MODE B — Direct Count Injection (for exact replay/debugging):
    At each timestep, reads from a saved session JSON and sets lane queues
    to match exactly what was observed at that timestamp.
    """

    MODE_CALIBRATED = "calibrated_stochastic"
    MODE_REPLAY = "direct_count_injection"

    def __init__(
        self,
        flow_params: TrafficFlowParams,
        mode: str = "calibrated_stochastic",
    ) -> None:
        self.flow_params = flow_params
        self.mode = mode
        self._replay_frames: Optional[list] = None
        self._replay_index = 0

    def step(self, intersection, current_time_seconds: float, dt: float = 0.1) -> None:
        """
        Called each simulation tick.
        Spawns vehicles per calibrated arrival rates (Mode A)
        or injects exact counts from session replay (Mode B).
        """
        if self.mode == self.MODE_CALIBRATED:
            self._step_calibrated(intersection, dt)
        elif self.mode == self.MODE_REPLAY and self._replay_frames:
            self._step_replay(intersection, current_time_seconds)

    def _step_calibrated(self, intersection, dt: float) -> None:
        """
        Poisson arrivals with calibrated lambda values per lane.
        Vehicle types sampled from calibrated type distribution.
        """
        spawn_rates = self.flow_params.spawn_rates

        for lane_key in LANE_KEYS:
            # spawn_rates is in vehicles/minute -> convert to per-tick rate
            lambda_per_min = spawn_rates.get(lane_key, 0.8)
            lambda_per_tick = lambda_per_min * dt / 60.0

            # Poisson arrival
            arrivals = np.random.poisson(lambda_per_tick)
            for _ in range(arrivals):
                vehicle_type = self._sample_vehicle_type()
                # Try to spawn in the intersection
                try:
                    intersection.spawn_vehicle(lane_key, vehicle_type=vehicle_type)
                except Exception:
                    pass  # Queue full — skip this spawn

    def _step_replay(self, intersection, current_time_seconds: float) -> None:
        """
        Direct count injection from saved session data.
        Sets lane queues to match recorded observation at this timestamp.
        """
        if not self._replay_frames or self._replay_index >= len(self._replay_frames):
            return

        frame = self._replay_frames[self._replay_index]
        raw_counts = frame.get("raw_counts", {})

        for lane_key, target_count in raw_counts.items():
            # Adjust current queue toward target
            try:
                current_count = len(intersection.get_queue(lane_key))
                delta = target_count - current_count
                if delta > 0:
                    for _ in range(delta):
                        vehicle_type = self._sample_vehicle_type()
                        intersection.spawn_vehicle(lane_key, vehicle_type=vehicle_type)
            except Exception:
                pass

        self._replay_index += 1

    def _sample_vehicle_type(self) -> str:
        """Sample a vehicle type from the calibrated distribution."""
        dist = self.flow_params.vehicle_type_distribution
        if not dist:
            return "car"
        types = list(dist.keys())
        probs = list(dist.values())
        total = sum(probs)
        if total <= 0:
            return "car"
        probs = [p / total for p in probs]
        return random.choices(types, weights=probs, k=1)[0]

    def load_replay_session(self, session_json_path: str) -> None:
        """Load a session JSON for Mode B replay."""
        import json
        with open(session_json_path) as f:
            data = json.load(f)
        self._replay_frames = data.get("frames", [])
        self._replay_index = 0

    def set_time_period(self, period: str) -> None:
        """
        Switch between time periods: morning_peak / evening_peak / off_peak.
        Updates flow_params.time_period for logging.
        """
        self.flow_params.time_period = period
        print(f"[RealWorldSpawner] Switched to time period: {period}")

    def get_current_spawn_rates(self) -> Dict[str, float]:
        """Returns current lambda per lane (vehicles/minute)."""
        return dict(self.flow_params.spawn_rates)
