"""
traffic_math.py — Shared Traffic Engineering Computation Library
=================================================================
Task 1.4 (BUG-04): Provides the canonical DEST_MAP (movement → outgoing direction)
and shared pressure calculation functions used by BOTH simulation (environment.py)
and real-world vision pipeline (state_builder.py).

Centralizing these ensures the Sim-to-Real observation is numerically identical.
Any future changes to the pressure formula must only happen here.
"""
from __future__ import annotations

from typing import Dict

import numpy as np

# ---------------------------------------------------------------------------
# Canonical movement → outgoing direction mapping (12 traffic movements)
# Must be identical in environment.py and state_builder.py.
# ---------------------------------------------------------------------------
DEST_MAP: Dict[str, str] = {
    "north_straight": "south",
    "north_left":     "east",
    "north_right":    "west",
    "south_straight": "north",
    "south_left":     "west",
    "south_right":    "east",
    "east_straight":  "west",
    "east_left":      "south",
    "east_right":     "north",
    "west_straight":  "east",
    "west_left":      "north",
    "west_right":     "south",
}

# Canonical movement ordering for state vector (dims 0-11)
MOVEMENT_KEYS = [
    "north_straight", "north_left",  "north_right",
    "south_straight", "south_left",  "south_right",
    "east_straight",  "east_left",   "east_right",
    "west_straight",  "west_left",   "west_right",
]

# Max lane capacity for normalization
MAX_CAP: float = 10.0


def compute_movement_pressures(
    movement_queues: Dict[str, int],
    outgoing_counts: Dict[str, int],
    max_cap: float = MAX_CAP,
) -> Dict[str, float]:
    """
    Compute destination-aware traffic pressure per movement.

    Formula (MPLight / PressLight):
        pressure(m) = max(0, incoming(m)/cap - outgoing(dest(m))/cap)

    Args:
        movement_queues: Per-movement queue length dict (12 keys).
        outgoing_counts: Per-direction outgoing vehicle counts (4 keys).
        max_cap: Lane capacity for normalization.

    Returns:
        Dict mapping movement → pressure ∈ [0, 1].
    """
    pressures: Dict[str, float] = {}
    for movement, dest in DEST_MAP.items():
        incoming = movement_queues.get(movement, 0) / max_cap
        out = outgoing_counts.get(dest, 0) / max_cap
        pressures[movement] = max(0.0, incoming - out)
    return pressures


def compute_total_pressure(pressures: Dict[str, float]) -> float:
    """Sum all 12 movement pressures."""
    return sum(pressures.values())


def normalize_total_pressure(total_pressure: float, scale: float = 20.0) -> float:
    """Normalize total pressure to [0, 1] range (scale = sum of 20 max pressures)."""
    return min(1.0, total_pressure / scale)


def compute_phase_pressure(pressures: Dict[str, float], phase: int) -> float:
    """
    Sum movement pressures for the movements active in the given phase.

    Phase mapping:
        0 = NS_STRAIGHT: north_straight, south_straight
        1 = EW_STRAIGHT: east_straight, west_straight
        2 = NS_LEFT:     north_left, south_left
        3 = EW_LEFT:     east_left, west_left
    """
    _PHASE_MOVEMENTS = {
        0: ["north_straight", "south_straight"],
        1: ["east_straight", "west_straight"],
        2: ["north_left", "south_left"],
        3: ["east_left", "west_left"],
    }
    movements = _PHASE_MOVEMENTS.get(phase, [])
    return sum(pressures.get(m, 0.0) for m in movements)


def build_queue_obs_vector(movement_queues: Dict[str, int], max_cap: float = MAX_CAP) -> np.ndarray:
    """
    Build the 12-element queue observation vector in canonical MOVEMENT_KEYS order.

    Returns float32 array of shape (12,), values in [0, 1].
    """
    return np.array(
        [min(1.0, movement_queues.get(k, 0) / max_cap) for k in MOVEMENT_KEYS],
        dtype=np.float32,
    )
