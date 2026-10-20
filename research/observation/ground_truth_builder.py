"""
ground_truth_builder.py — Simulator Ground-Truth State Builder (Oracle Only)
=============================================================================
Extracts complete, uncorrupted microscopic traffic state from the simulation
engine. Used exclusively for evaluation, ground-truth error measurement,
and theoretical upper-bound oracle benchmarks.

POLICY WARNING:
The RL controller must NEVER receive ground-truth oracle observations during
camera-mode evaluation or deployment.
"""
from __future__ import annotations

from typing import Any, Dict
import numpy as np

from server.app.simulation.intersection import Intersection
from server.app.simulation.traffic_math import (
    MAX_CAP,
    MOVEMENT_KEYS,
    compute_movement_pressures,
    compute_total_pressure,
    normalize_total_pressure,
)
from server.app.simulation.demand_forecast import ArrivalForecaster


class GroundTruthStateBuilder:
    """
    Builds oracle state representation with full simulator omniscience:
    - Exact vehicle counts across entire lane lengths (including unobserved zones)
    - Full downstream departure road occupancies
    - Uncorrupted signal timers
    - True vehicle waiting time distribution
    """

    def __init__(self, forecaster: ArrivalForecaster | None = None) -> None:
        self.forecaster = forecaster or ArrivalForecaster()

    def build_oracle_state(self, intersection: Intersection) -> np.ndarray:
        """
        Extract complete 28-D ground truth observation.
        """
        queues = intersection.get_movement_queues()
        signal = intersection.signal
        outgoing = intersection.get_outgoing_counts()

        # Dims 0-11: exact movement queues with tanh normalization
        movements = [
            float(np.tanh(queues.get(k, 0) / 15.0))
            for k in MOVEMENT_KEYS
        ]

        # Dims 12-15: exact active phase one-hot
        phase_onehot = [0.0, 0.0, 0.0, 0.0]
        phase_onehot[signal.current_phase] = 1.0

        # Dim 16: exact normalized time in phase
        time_norm = min(1.0, signal.time_in_phase / signal.MAX_GREEN_TIME)

        # Dim 17: exact transition indicator
        is_trans = 1.0 if signal.color.name in ("YELLOW", "RED") else 0.0

        # Dim 18: exact network pressure
        pressures = compute_movement_pressures(queues, outgoing, MAX_CAP)
        total_p = compute_total_pressure(pressures)
        pressure_norm = normalize_total_pressure(total_p)

        # Dim 19: exact maximum starvation timer
        starv_timers = list(signal.phase_starvation_timer.values())
        max_starv = min(max(starv_timers) / signal.STARVATION_THRESHOLD, 1.0) if starv_timers else 0.0

        # Dims 20-27: demand forecaster features
        forecast = self.forecaster.get_forecast_features().tolist()

        return np.array(
            movements + phase_onehot + [time_norm, is_trans, pressure_norm, max_starv] + forecast,
            dtype=np.float32,
        )

    def get_ground_truth_diagnostics(self, intersection: Intersection) -> Dict[str, Any]:
        """Return raw unnormalized physics metrics for error auditing."""
        queues = intersection.get_movement_queues()
        total_waiting = intersection.get_total_waiting()
        outgoing = intersection.get_outgoing_counts()
        return {
            "movement_queues": queues,
            "total_waiting": total_waiting,
            "outgoing_counts": outgoing,
            "spawner_backlog": sum(intersection.spawner.get_backlog_counts().values()),
            "total_passed": intersection.total_passed,
            "total_generated": intersection.spawner.total_generated,
        }
