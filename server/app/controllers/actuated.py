"""
actuated.py — NEMA Actuated / Variable-Access-Timer (VAT) Signal Controller Baseline
====================================================================================
Implements classical NEMA dual-ring actuated signal control:
- Serves green until gap-out condition (no arrivals for gap_threshold AND min_green served).
- Enforces max_green hard ceiling.
- At termination of green, transitions to highest-demand conflicting phase.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
import numpy as np

from .base import BaseController, ControllerCapabilities, ControllerContext
from ..simulation.traffic_math import MOVEMENT_KEYS

_GAP_THRESHOLD  = 3.5   # seconds without arrivals triggers gap-out
_MIN_GREEN_TIME = 8.0   # minimum green before gap-out allowed
_MAX_GREEN_TIME = 40.0  # hard ceiling per phase

PHASE_MOVEMENTS: Dict[int, List[str]] = {
    0: ["north_straight", "south_straight", "north_right", "south_right"],
    1: ["east_straight",  "west_straight",  "east_right",  "west_right"],
    2: ["north_left",      "south_left"],
    3: ["east_left",       "west_left"],
}


class ActuatedController(BaseController):
    """
    NEMA Actuated / Variable-Access-Timer (VAT) controller baseline.

    Args:
        gap_threshold: Seconds without arrival before gap-out (default 3.5s).
        min_green: Minimum green duration before gap-out allowed (default 8.0s).
        max_green: Maximum green time ceiling (default 40.0s).
    """

    def __init__(
        self,
        gap_threshold: float = _GAP_THRESHOLD,
        min_green: float = _MIN_GREEN_TIME,
        max_green: float = _MAX_GREEN_TIME,
    ) -> None:
        super().__init__(name="actuated")
        self.gap_threshold = gap_threshold
        self.min_green = min_green
        self.max_green = max_green

        self._time_since_last_arrival: float = 0.0
        self._current_phase: int = 0
        self._time_in_phase: float = 0.0

    def reset(self, seed: Optional[int] = None) -> None:
        super().reset(seed=seed)
        self._time_since_last_arrival = 0.0
        self._current_phase = 0
        self._time_in_phase = 0.0

    def get_capabilities(self) -> ControllerCapabilities:
        return ControllerCapabilities(
            name="actuated",
            version="1.0.0",
            supports_uncertainty=False,
            supports_fallback=False,
            supports_training=False,
            uses_camera_observable_state_only=True,
            is_learning_based=False,
            description="NEMA Actuated / Variable-Access-Timer controller with gap-out logic",
        )

    def update_arrivals(self, arrivals_this_tick: int, dt: float = 0.1) -> None:
        """Call when arrival data is available to update gap timer."""
        if arrivals_this_tick > 0:
            self._time_since_last_arrival = 0.0
        else:
            self._time_since_last_arrival += dt

    def act(self, observation: np.ndarray, context: ControllerContext) -> int:
        self._step_count += 1
        self._time_in_phase += context.dt

        # Check arrivals from context if available
        spawned = context.extra_telemetry.get("spawned_this_step", 0)
        self.update_arrivals(spawned, dt=context.dt)

        # Gap-out condition
        gap_out = (
            self._time_in_phase >= self.min_green
            and self._time_since_last_arrival >= self.gap_threshold
        )
        max_green_exceeded = self._time_in_phase >= self.max_green

        should_switch = (gap_out or max_green_exceeded) and context.can_switch_phase

        if should_switch:
            # Pick next phase with highest queue
            phase_counts: Dict[int, float] = {}
            if context.movement_queues is not None:
                for ph, movements in PHASE_MOVEMENTS.items():
                    phase_counts[ph] = sum(context.movement_queues.get(m, 0) for m in movements)
            else:
                for ph, movements in PHASE_MOVEMENTS.items():
                    phase_counts[ph] = sum(
                        float(observation[MOVEMENT_KEYS.index(m)])
                        for m in movements
                        if m in MOVEMENT_KEYS and MOVEMENT_KEYS.index(m) < len(observation)
                    )

            # Look at alternative phases
            candidates = [p for p in range(4) if p != self._current_phase]
            best_alt = max(candidates, key=lambda p: (phase_counts.get(p, 0.0), -p))

            # Only switch if candidate has vehicles or if current phase has reached max-green
            if phase_counts.get(best_alt, 0.0) > 0.0 or max_green_exceeded:
                self._current_phase = best_alt
                self._time_in_phase = 0.0
                self._time_since_last_arrival = 0.0

        self._last_diagnostics = {
            "controller": "actuated",
            "current_phase": self._current_phase,
            "time_in_phase": self._time_in_phase,
            "time_since_last_arrival": self._time_since_last_arrival,
            "gap_out": gap_out,
            "max_green_exceeded": max_green_exceeded,
        }
        return self._current_phase
