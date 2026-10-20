"""Greedy max-queue traffic signal controller baseline."""
from __future__ import annotations

from typing import Dict, List, Optional
import numpy as np

from .base import BaseController, ControllerCapabilities, ControllerContext

PHASE_MOVEMENTS: Dict[int, List[str]] = {
    0: ["north_straight", "south_straight", "north_right", "south_right"],
    1: ["east_straight", "west_straight", "east_right", "west_right"],
    2: ["north_left", "south_left"],
    3: ["east_left", "west_left"],
}

# Mapping canonical MOVEMENT_KEYS indices (0-11) to phases
PHASE_OBS_INDICES: Dict[int, List[int]] = {
    0: [0, 2, 3, 5],     # north_straight, north_right, south_straight, south_right
    1: [6, 8, 9, 11],    # east_straight, east_right, west_straight, west_right
    2: [1, 4],           # north_left, south_left
    3: [7, 10],          # east_left, west_left
}


class GreedyController(BaseController):
    """Greedy controller prioritizing the phase with largest instantaneous queue."""

    def __init__(self) -> None:
        super().__init__(name="greedy")

    def reset(self, seed: Optional[int] = None) -> None:
        super().reset(seed=seed)

    def get_capabilities(self) -> ControllerCapabilities:
        return ControllerCapabilities(
            name="greedy",
            version="1.0.0",
            supports_uncertainty=False,
            supports_fallback=False,
            supports_training=False,
            uses_camera_observable_state_only=True,
            is_learning_based=False,
            description="Greedy max-queue controller serving approach with greatest backlog",
        )

    def act(self, observation: np.ndarray, context: ControllerContext) -> int:
        self._step_count += 1
        phase_demands: Dict[int, float] = {}

        if context.movement_queues is not None:
            for ph, movements in PHASE_MOVEMENTS.items():
                phase_demands[ph] = sum(context.movement_queues.get(m, 0) for m in movements)
        else:
            obs_queues = observation[:12]
            for ph, idxs in PHASE_OBS_INDICES.items():
                phase_demands[ph] = sum(float(obs_queues[i]) for i in idxs if i < len(obs_queues))

        current_phase = context.current_phase
        current_demand = phase_demands.get(current_phase, 0.0)
        max_demand = max(phase_demands.values()) if phase_demands else 0.0

        # Preserve green if current phase is tied for maximum or if all queues are empty
        if (current_demand >= max_demand and current_demand > 0.0) or max_demand == 0.0:
            selected_phase = current_phase
        else:
            selected_phase = max(phase_demands, key=lambda p: (phase_demands[p], -p))

        action = selected_phase if context.can_switch_phase else current_phase

        self._last_diagnostics = {
            "controller": "greedy",
            "phase_demands": phase_demands,
            "current_phase": current_phase,
            "selected_phase": action,
            "max_demand": max_demand,
        }
        return action
