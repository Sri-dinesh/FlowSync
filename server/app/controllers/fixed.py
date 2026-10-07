"""Pre-timed fixed-cycle traffic signal controller baseline (Webster 1958)."""
from __future__ import annotations

from typing import List, Optional
import numpy as np

from .base import BaseController, ControllerCapabilities, ControllerContext


class FixedController(BaseController):
    """
    Fixed-Time cycle controller based on Webster's pre-timed formulation.

    Args:
        phase_durations: List of durations (seconds) for phases 0, 1, 2, 3.
                         Default is 8.0s per phase (32s full cycle).
    """

    def __init__(self, phase_durations: Optional[List[float]] = None) -> None:
        super().__init__(name="fixed")
        self.phase_durations = phase_durations or [8.0, 8.0, 8.0, 8.0]
        self._current_phase: int = 0
        self._time_in_phase: float = 0.0

    def reset(self, seed: Optional[int] = None) -> None:
        super().reset(seed=seed)
        self._current_phase = 0
        self._time_in_phase = 0.0

    def get_capabilities(self) -> ControllerCapabilities:
        return ControllerCapabilities(
            name="fixed",
            version="1.0.0",
            supports_uncertainty=False,
            supports_fallback=False,
            supports_training=False,
            uses_camera_observable_state_only=True,
            is_learning_based=False,
            description="Classical pre-timed fixed-cycle controller (Webster 1958)",
        )

    def act(self, observation: np.ndarray, context: ControllerContext) -> int:
        self._step_count += 1
        self._time_in_phase += context.dt
        phase_cap = self.phase_durations[self._current_phase]

        if context.can_switch_phase and self._time_in_phase >= phase_cap:
            self._current_phase = (self._current_phase + 1) % 4
            self._time_in_phase = 0.0

        self._last_diagnostics = {
            "controller": "fixed",
            "selected_phase": self._current_phase,
            "time_in_phase": self._time_in_phase,
            "phase_duration": phase_cap,
        }
        return self._current_phase
