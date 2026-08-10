"""
StateBuilder — Convert YOLO+ROI output → 20-dim RL observation vector.
Drop-in replacement for simulation obs builder. Numerically identical output.
"""
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from ..models.config import (
    LANE_KEYS,
    MAX_GREEN_TIME,
    MAX_QUEUE_CAP,
    OBS_DIM,
    STARVATION_THRESHOLD,
)
from ..models.schemas import WeightedLaneCounts


class StateBuilder:
    """
    Converts real-world vehicle detections to the same 20-dim observation vector
    used by the simulation's DQN agent. This is the bridge between real-world and RL.

    Observation vector (20 dims) — identical structure to simulation:
    Dims 0-11:  Weighted queue per movement lane (normalized by MAX_QUEUE_CAP=10.0)
    Dims 12-15: One-hot current signal phase (4 dims)
    Dim  16:    Time in current phase / MAX_GREEN_TIME (normalized)
    Dim  17:    Is transitioning (1.0 if yellow/all-red, 0.0 if green)
    Dim  18:    Total pressure (sum of dims 0-11, normalized by 20.0)
    Dim  19:    Starvation score (max wait time / STARVATION_THRESHOLD)
    """

    def __init__(self) -> None:
        pass

    def build(
        self,
        weighted_counts: WeightedLaneCounts,
        current_phase: int,
        time_in_phase_seconds: float,
        is_transitioning: bool,
        starvation_scores: Optional[Dict[str, float]] = None,
    ) -> np.ndarray:
        """
        Returns: float32 array of shape (20,), all values in [0.0, 1.0]
        """
        obs = np.zeros(OBS_DIM, dtype=np.float32)

        # Dims 0-11: normalized weighted queue per lane
        counts_dict = weighted_counts.to_dict()
        for i, lane in enumerate(LANE_KEYS):
            obs[i] = self._normalize_queue(counts_dict.get(lane, 0.0))

        # Dims 12-15: one-hot signal phase
        if 0 <= current_phase < 4:
            obs[12 + current_phase] = 1.0

        # Dim 16: normalized time in phase
        obs[16] = min(1.0, time_in_phase_seconds / MAX_GREEN_TIME)

        # Dim 17: is transitioning (yellow/all-red clearance)
        obs[17] = 1.0 if is_transitioning else 0.0

        # Dim 18: total pressure (sum of normalized queues / 20.0)
        obs[18] = self._compute_pressure(weighted_counts)

        # Dim 19: starvation score
        if starvation_scores:
            max_wait = max(starvation_scores.values()) if starvation_scores else 0.0
            obs[19] = min(1.0, max_wait / STARVATION_THRESHOLD)
        else:
            obs[19] = 0.0

        return obs

    def _normalize_queue(self, weighted_count: float) -> float:
        """weighted_count / MAX_QUEUE_CAP, clamped to [0, 1]."""
        return float(min(1.0, max(0.0, weighted_count / MAX_QUEUE_CAP)))

    def _compute_pressure(self, weighted_counts: WeightedLaneCounts) -> float:
        """Sum of all 12 normalized queues / 20.0."""
        total = sum(
            self._normalize_queue(v) for v in weighted_counts.to_dict().values()
        )
        return min(1.0, total / 20.0)

    def get_obs_description(self, obs: np.ndarray) -> Dict[str, float]:
        """Returns labeled dict of observation for debugging/display."""
        desc: Dict[str, float] = {}
        for i, lane in enumerate(LANE_KEYS):
            desc[f"queue_{lane}"] = float(obs[i])
        phase_names = ["NS_STRAIGHT", "EW_STRAIGHT", "NS_LEFT", "EW_LEFT"]
        for i, name in enumerate(phase_names):
            desc[f"phase_{name}"] = float(obs[12 + i])
        desc["time_in_phase"] = float(obs[16])
        desc["is_transitioning"] = float(obs[17])
        desc["total_pressure"] = float(obs[18])
        desc["starvation_score"] = float(obs[19])
        return desc
