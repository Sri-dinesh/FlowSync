"""
vat_controller.py — Variable-Access-Timer (VAT) / Actuated Signal Controller
==============================================================================
Task 8.1: Implements the classical NEMA/VAT actuated controller baseline for
literature-standard four-way comparisons: Fixed vs. VAT vs. Greedy vs. FlowSync AI.

The VAT controller:
1. Serves each green phase until a "gap-out" condition is met:
   Gap-out = no vehicle arrival detected for GAP_THRESHOLD seconds AND
   minimum green time has been served.
2. If no gap-out occurs, serves until the MAX_GREEN_TIME hard cap.
3. At gap-out or max-green, switches to the next phase with highest queue.

This mimics real-world NEMA actuated controllers used at most traffic signals.

Usage:
    vat = VATController(intersection)
    action = vat.select_action()  # returns 0-3
    intersection.tick(dt=0.1, action=action)
    vat.update(dt=0.1, spawned_this_step=n)
"""
from __future__ import annotations

import logging
from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .intersection import Intersection

logger = logging.getLogger(__name__)

# ── VAT Parameters (classical NEMA actuated) ────────────────────────────────
_GAP_THRESHOLD    = 3.5    # seconds: gap-out if no vehicle for this long
_MIN_GREEN_TIME   = 8.0    # seconds: minimum before gap-out can occur
_MAX_GREEN_TIME   = 40.0   # seconds: hard cap per phase
_PHASE_DIRECTIONS = {
    0: ["north_straight", "south_straight", "north_right", "south_right"],
    1: ["east_straight",  "west_straight",  "east_right",  "west_right"],
    2: ["north_left",     "south_left"],
    3: ["east_left",      "west_left"],
}


class VATController:
    """
    Variable-Access-Timer actuated traffic controller.

    Provides a physically realistic baseline that outperforms Fixed-Timer
    by responding to vehicle arrivals, but cannot look ahead (unlike RL + forecaster).

    Args:
        intersection: The Intersection object to control.
        gap_threshold: Seconds of no activity before gap-out triggers.
        min_green: Minimum green time before gap-out is allowed.
        max_green: Maximum green time hard cap.
    """

    def __init__(
        self,
        intersection: "Intersection",
        gap_threshold: float = _GAP_THRESHOLD,
        min_green: float = _MIN_GREEN_TIME,
        max_green: float = _MAX_GREEN_TIME,
    ) -> None:
        self.intersection = intersection
        self.gap_threshold = gap_threshold
        self.min_green = min_green
        self.max_green = max_green

        self._time_since_last_arrival: float = 0.0
        self._current_phase: int = 0
        self._time_in_phase: float = 0.0
        self._switched: bool = False  # prevent repeated switches per tick

    def update(self, dt: float, spawned_this_step: int) -> None:
        """
        Update VAT internal timers.

        Args:
            dt: Time delta (seconds).
            spawned_this_step: Vehicles spawned/arriving this tick.
        """
        self._time_in_phase += dt

        if spawned_this_step > 0:
            # Reset gap timer on any vehicle arrival
            self._time_since_last_arrival = 0.0
        else:
            self._time_since_last_arrival += dt

        self._switched = False

    def select_action(self) -> int:
        """
        Select phase action per VAT logic.

        Gap-out condition: min_green served AND no vehicle for gap_threshold seconds.
        Max-green condition: time_in_phase >= max_green.

        Returns: phase index (0-3) to pass to intersection.tick().
        """
        signal = self.intersection.signal

        # During yellow/all-red transitions, maintain pending phase
        if signal.color.name in ("YELLOW", "RED"):
            return signal.current_phase

        # Hard cap: max-green exceeded
        if self._time_in_phase >= self.max_green:
            new_phase = self._pick_highest_queue_phase()
            if new_phase != self._current_phase:
                logger.debug(
                    "VAT max-green triggered at %.1fs. Switching phase %d → %d.",
                    self._time_in_phase,
                    self._current_phase,
                    new_phase,
                )
                self._current_phase = new_phase
                self._time_in_phase = 0.0
                self._time_since_last_arrival = 0.0
            return self._current_phase

        # Gap-out: min green served AND no recent arrivals
        if (
            self._time_in_phase >= self.min_green
            and self._time_since_last_arrival >= self.gap_threshold
        ):
            new_phase = self._pick_highest_queue_phase()
            if new_phase != self._current_phase:
                logger.debug(
                    "VAT gap-out at %.1fs (gap=%.1fs). Switching phase %d → %d.",
                    self._time_in_phase,
                    self._time_since_last_arrival,
                    self._current_phase,
                    new_phase,
                )
                self._current_phase = new_phase
                self._time_in_phase = 0.0
                self._time_since_last_arrival = 0.0
            return self._current_phase

        # Continue serving current phase
        return self._current_phase

    def _pick_highest_queue_phase(self) -> int:
        """Select the phase with the most waiting vehicles, excluding current phase."""
        queues = self.intersection.get_movement_queues()
        best_phase = self._current_phase
        best_count = -1

        for phase, movements in _PHASE_DIRECTIONS.items():
            if phase == self._current_phase:
                continue
            count = sum(queues.get(m, 0) for m in movements)
            if count > best_count:
                best_count = count
                best_phase = phase

        # Fallback: if all phases empty, advance sequentially
        if best_count == 0:
            best_phase = (self._current_phase + 1) % 4

        return best_phase

    def reset(self) -> None:
        """Reset VAT state (call at episode/evaluation start)."""
        self._time_since_last_arrival = 0.0
        self._current_phase = 0
        self._time_in_phase = 0.0
        self._switched = False
