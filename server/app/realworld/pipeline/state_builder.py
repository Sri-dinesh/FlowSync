"""
StateBuilder — Convert YOLO+ROI output → 20-dim RL observation vector.
=========================================================================
BUG-04 Fix: Previously this module computed pressure (Dim 18) as a simple
sum of all 12 normalized queues / 20.0, while environment.py computed
destination-aware movement pressure (incoming/cap - outgoing/cap).

This mismatch caused Sim-to-Real policy breakdown: the agent was trained on
destination-aware pressure but received raw queue-sum pressure in real-world mode.

Corrected: Dim 18 now uses compute_movement_pressures() from traffic_math.py —
the same function used by environment.py — providing numerically identical
pressure signals in both simulation training and real-world deployment.
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

# BUG-04 Fix: import canonical shared pressure computation
from ...simulation.traffic_math import (
    DEST_MAP,
    MOVEMENT_KEYS,
    compute_movement_pressures,
    compute_total_pressure,
    normalize_total_pressure,
)


class StateBuilder:
    """
    Converts real-world vehicle detections to the same 20-dim observation vector
    used by the simulation's DQN agent. This is the bridge between real-world and RL.

    Observation vector (20 dims) — identical structure to simulation:
    Dims 0-11:  Weighted queue per movement lane (normalized by MAX_QUEUE_CAP=10.0)
    Dims 12-15: One-hot current signal phase (4 dims)
    Dim  16:    Time in current phase / MAX_GREEN_TIME (normalized)
    Dim  17:    Is transitioning (1.0 if yellow/all-red, 0.0 if green)
    Dim  18:    Destination-aware total pressure (BUG-04 fix: uses shared DEST_MAP)
    Dim  19:    Starvation score (max wait time / STARVATION_THRESHOLD)

    BUG-04 Change:
    - OLD (broken): obs[18] = sum(normalized_queues) / 20.0
    - NEW (correct): obs[18] = normalize(sum(compute_movement_pressures(queues, outgoing)))
      where compute_movement_pressures uses DEST_MAP to subtract downstream occupancy.
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
        outgoing_counts: Optional[Dict[str, int]] = None,
    ) -> np.ndarray:
        """
        Returns: float32 array of shape (20,), all values in [0.0, 1.0]

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

        # Dim 17: is transitioning (yellow/all-red clearance)
        obs[17] = 1.0 if is_transitioning else 0.0

        # Dim 18: BUG-04 CORRECTED — destination-aware total pressure
        # Build integer queue counts from weighted float counts (approximate)
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

        return obs

    def _normalize_queue(self, weighted_count: float) -> float:
        """weighted_count / MAX_QUEUE_CAP, clamped to [0, 1]."""
        return float(min(1.0, max(0.0, weighted_count / MAX_QUEUE_CAP)))

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
        return desc
