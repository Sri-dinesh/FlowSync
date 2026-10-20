"""Decentralized Max-Pressure traffic signal controller baseline (Varaiya 2013)."""
from __future__ import annotations

from typing import Dict, List, Optional
import numpy as np

from .base import BaseController, ControllerCapabilities, ControllerContext
from ..simulation.traffic_math import DEST_MAP, MAX_CAP, MOVEMENT_KEYS

PHASE_MOVEMENTS: Dict[int, List[str]] = {
    0: ["north_straight", "south_straight"],
    1: ["east_straight",  "west_straight"],
    2: ["north_left",      "south_left"],
    3: ["east_left",       "west_left"],
}

# Movement indices in canonical MOVEMENT_KEYS list
MOVEMENT_INDEX: Dict[str, int] = {k: i for i, k in enumerate(MOVEMENT_KEYS)}


class MaxPressureController(BaseController):
    """
    Max-Pressure controller implementing Varaiya's stabilized network queue optimization.

    Args:
        max_cap_in: Upstream approach lane capacity for normalization (default 10.0).
        max_cap_out: Downstream departure lane capacity for normalization (default 10.0).
    """

    def __init__(self, max_cap_in: float = MAX_CAP, max_cap_out: float = MAX_CAP) -> None:
        super().__init__(name="max_pressure")
        self.max_cap_in = max_cap_in
        self.max_cap_out = max_cap_out

    def reset(self, seed: Optional[int] = None) -> None:
        super().reset(seed=seed)

    def get_capabilities(self) -> ControllerCapabilities:
        return ControllerCapabilities(
            name="max_pressure",
            version="1.0.0",
            supports_uncertainty=False,
            supports_fallback=False,
            supports_training=False,
            uses_camera_observable_state_only=True,
            is_learning_based=False,
            description="Classical Max-Pressure network queue balancing controller (Varaiya 2013)",
        )

    def compute_movement_pressures(
        self,
        movement_queues: Dict[str, float],
        outgoing_counts: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Compute pressure per movement: P(m) = max(0, q_in(m)/cap_in - q_out(dest(m))/cap_out).
        """
        pressures: Dict[str, float] = {}
        for movement, dest in DEST_MAP.items():
            q_in = movement_queues.get(movement, 0.0) / self.max_cap_in
            q_out = outgoing_counts.get(dest, 0.0) / self.max_cap_out
            pressures[movement] = max(0.0, float(q_in - q_out))
        return pressures

    def compute_phase_pressures(
        self, movement_pressures: Dict[str, float]
    ) -> Dict[int, float]:
        """Sum movement pressures for each signal phase."""
        phase_pressures: Dict[int, float] = {}
        for phase, movements in PHASE_MOVEMENTS.items():
            phase_pressures[phase] = sum(
                movement_pressures.get(m, 0.0) for m in movements
            )
        return phase_pressures

    def act(self, observation: np.ndarray, context: ControllerContext) -> int:
        self._step_count += 1

        if context.movement_queues is not None:
            queues = {k: float(v) for k, v in context.movement_queues.items()}
        else:
            queues = {
                MOVEMENT_KEYS[i]: float(observation[i]) * self.max_cap_in
                for i in range(min(12, len(observation)))
            }

        outgoing = (
            {k: float(v) for k, v in context.outgoing_counts.items()}
            if context.outgoing_counts is not None
            else {d: 0.0 for d in ["north", "south", "east", "west"]}
        )

        movement_pressures = self.compute_movement_pressures(queues, outgoing)
        phase_pressures = self.compute_phase_pressures(movement_pressures)

        current_phase = context.current_phase
        current_press = phase_pressures.get(current_phase, 0.0)
        max_press = max(phase_pressures.values()) if phase_pressures else 0.0

        # Preserve green if current phase is tied for maximum or if all pressures are zero
        if (current_press >= max_press and current_press > 0.0) or max_press == 0.0:
            selected_phase = current_phase
        else:
            selected_phase = max(phase_pressures, key=lambda p: (phase_pressures[p], -p))

        action = selected_phase if context.can_switch_phase else current_phase

        self._last_diagnostics = {
            "controller": "max_pressure",
            "phase_pressures": phase_pressures,
            "movement_pressures": movement_pressures,
            "current_phase": current_phase,
            "selected_phase": action,
            "max_pressure": max_press,
        }
        return action
