"""
Exponential Moving Average smoother for vehicle queue counts across frames.
Prevents single-frame detection errors from causing erratic signal decisions.
"""
from __future__ import annotations

from typing import Dict

from ..models.config import LANE_KEYS, TEMPORAL_SMOOTHING_ALPHA


class TemporalSmoother:
    """
    Smooths per-lane vehicle counts across frames using EMA.

    alpha = 0.3: new_value = 0.3 * current + 0.7 * previous
    Lower alpha = more smoothing (less reactive).
    Higher alpha = more reactive (closer to raw values).
    """

    def __init__(self, alpha: float = TEMPORAL_SMOOTHING_ALPHA) -> None:
        self.alpha = alpha
        self._state: Dict[str, float] = {lane: 0.0 for lane in LANE_KEYS}
        self._initialized = False

    def update(self, raw_counts: Dict[str, float]) -> Dict[str, float]:
        """
        Apply EMA to raw lane counts and return smoothed values.
        On first call, initializes state to raw values (no smoothing).
        """
        if not self._initialized:
            self._state = {lane: float(raw_counts.get(lane, 0.0)) for lane in LANE_KEYS}
            self._initialized = True
        else:
            for lane in LANE_KEYS:
                raw = float(raw_counts.get(lane, 0.0))
                self._state[lane] = self.alpha * raw + (1.0 - self.alpha) * self._state[lane]
        return dict(self._state)

    def reset(self) -> None:
        """Clear state between video sessions."""
        self._state = {lane: 0.0 for lane in LANE_KEYS}
        self._initialized = False

    def get_current(self) -> Dict[str, float]:
        """Return current smoothed state without updating."""
        return dict(self._state)

    def get_lane(self, lane: str) -> float:
        """Return smoothed value for a specific lane."""
        return self._state.get(lane, 0.0)
