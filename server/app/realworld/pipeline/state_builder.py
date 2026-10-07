"""Constructs the canonical 28-dimensional RL observation vector from camera detections."""
from __future__ import annotations

from typing import Dict, Optional

import numpy as np

from ..models.config import (
    LANE_KEYS,
    MAX_GREEN_TIME,
    MAX_QUEUE_CAP,
    OBS_DIM,
    STARVATION_THRESHOLD,
)
from ..models.schemas import WeightedLaneCounts
from ...simulation.traffic_math import (
    DEST_MAP,
    MOVEMENT_KEYS,
    compute_movement_pressures,
    compute_total_pressure,
    normalize_total_pressure,
)
from ...simulation.demand_forecast import ArrivalForecaster


class StateBuilder:
    """
    Constructs the 28-dimensional RL observation vector from camera detections:
      Dims 0-11:  Weighted queue per movement lane
      Dims 12-15: One-hot signal phase encoding
      Dim 16:     Normalized time in phase
      Dim 17:     Transitioning indicator (yellow / all-red clearance)
      Dim 18:     Destination-aware total pressure matching simulation environment
      Dim 19:     Normalized maximum starvation wait time
      Dims 20-27: Online EWMA arrival rate and trend features
    """

    def __init__(self) -> None:
        self._forecaster = ArrivalForecaster()
        self._previous_total: float = 0.0

    def build(
        self,
        weighted_counts: WeightedLaneCounts,
        current_phase: int,
        time_in_phase_seconds: float,
        is_transitioning: bool,
        starvation_scores: Optional[Dict[str, float]] = None,
        outgoing_counts: Optional[Dict[str, int]] = None,
        arrivals_since_last_frame: Optional[int] = None,
        frame_dt: float = 0.5,
    ) -> np.ndarray:
        """
        Returns: float32 array of shape (28,); growth/trend features may be signed.

        Args:
            weighted_counts: Per-lane weighted vehicle counts from YOLO pipeline.
            current_phase:   Current signal phase (0-3).
            time_in_phase_seconds: Time elapsed in current phase.
            is_transitioning: True during yellow/all-red clearance.
            starvation_scores: Optional per-direction wait time (seconds).
            outgoing_counts:  Optional per-direction downstream count estimate.
                              If None, pressure computation falls back to incoming-only
                              (equivalent to setting outgoing = 0 for all directions).
        """
        obs = np.zeros(OBS_DIM, dtype=np.float32)

        # Dims 0-11: normalized weighted queue per lane (canonical MOVEMENT_KEYS order)
        counts_dict = weighted_counts.to_dict()
        for i, lane in enumerate(LANE_KEYS):
            obs[i] = self._normalize_queue(counts_dict.get(lane, 0.0))

        # Dims 12-15: one-hot signal phase
        if 0 <= current_phase < 4:
            obs[12 + current_phase] = 1.0

        # Dim 16: normalized time in phase
        obs[16] = min(1.0, time_in_phase_seconds / MAX_GREEN_TIME)

        obs[17] = 1.0 if is_transitioning else 0.0

        # Destination-aware pressure matches simulation observation distribution.
        movement_queues = {
            lane: max(0, round(counts_dict.get(lane, 0.0)))
            for lane in MOVEMENT_KEYS
        }
        outgoing = outgoing_counts or {d: 0 for d in ["north", "south", "east", "west"]}
        pressures = compute_movement_pressures(
            movement_queues, outgoing, max_cap=MAX_QUEUE_CAP
        )
        total_pressure = compute_total_pressure(pressures)
        obs[18] = normalize_total_pressure(total_pressure)

        # Dim 19: starvation score
        if starvation_scores:
            max_wait = max(starvation_scores.values()) if starvation_scores else 0.0
            obs[19] = min(1.0, max_wait / STARVATION_THRESHOLD)
        else:
            obs[19] = 0.0

        # Dims 20-27: same EWMA feature implementation as simulation.  A caller
        # with tracker crossing events should supply arrivals_since_last_frame;
        # otherwise positive queue growth is used as a conservative proxy.
        current_total = float(sum(max(0.0, v) for v in counts_dict.values()))
        arrivals = (
            max(0, int(arrivals_since_last_frame))
            if arrivals_since_last_frame is not None
            else max(0, round(current_total - self._previous_total))
        )
        self._forecaster.tick(dt=max(frame_dt, 1e-3), spawned_this_step=arrivals)
        obs[20:28] = self._forecaster.get_forecast_features()
        self._previous_total = current_total

        return obs

    def _normalize_queue(self, weighted_count: float) -> float:
        """Match TrafficEnv's smooth queue saturation exactly."""
        return float(np.tanh(max(0.0, weighted_count) / 15.0))

    def get_obs_description(self, obs: np.ndarray) -> Dict[str, float]:
        """Returns labeled dict of observation for debugging/display."""
        desc: Dict[str, float] = {}
        for i, lane in enumerate(LANE_KEYS):
            desc[f"queue_{lane}"] = float(obs[i])
        phase_names = ["NS_STRAIGHT", "EW_STRAIGHT", "NS_LEFT", "EW_LEFT"]
        for i, name in enumerate(phase_names):
            desc[f"phase_{name}"] = float(obs[12 + i])
        desc["time_in_phase"]    = float(obs[16])
        desc["is_transitioning"] = float(obs[17])
        desc["total_pressure"]   = float(obs[18])
        desc["starvation_score"] = float(obs[19])
        for i, value in enumerate(obs[20:28], start=20):
            desc[f"forecast_{i - 20}"] = float(value)
        return desc
