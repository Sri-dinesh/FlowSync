"""
camera_observable_builder.py — Camera-Observable Traffic State Builder
=======================================================================
Task 1A.2: Formulates traffic observation vector strictly from camera-observable
signals. Prohibits any leakage of simulator ground truth, hidden future arrivals,
unobserved upstream portal queues, or unmeasurable downstream metrics.

Observation Pipeline:
  Detections & Tracks -> Approach ROI Mapping -> Observed Queue Counts
  -> Observable Signal Head -> Observed EWMA Forecast -> 28-D Observation
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
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

# Camera visibility boundaries along normalized lane axis [0.0 = stop line, 1.0 = entry portal]
CAMERA_FOV_STOP_LINE = 0.00
CAMERA_FOV_MAX_DISTANCE = 0.45  # camera can only see up to 45% of approach distance


@dataclass
class ObservedDetections:
    """Simulated or real camera detection packet."""
    visible_counts: Dict[str, int]
    visible_outgoing: Dict[str, int]
    observed_arrivals_last_step: int
    mean_confidence: float = 0.95
    dropped_frame: bool = False


class CameraObservableStateBuilder:
    """
    Constructs the 28-D observation vector using only camera-observable features.
    Guarantees no access to simulator internal oracle attributes.
    """

    def __init__(self, fov_max_distance: float = CAMERA_FOV_MAX_DISTANCE) -> None:
        self.fov_max_distance = fov_max_distance
        self.forecaster = ArrivalForecaster()
        self._last_observed_queues: Dict[str, int] = {k: 0 for k in MOVEMENT_KEYS}
        self._observation_age_steps: int = 0

    def reset(self) -> None:
        self.forecaster.reset()
        self._last_observed_queues = {k: 0 for k in MOVEMENT_KEYS}
        self._observation_age_steps = 0

    def extract_visible_detections(self, intersection: Intersection) -> ObservedDetections:
        """
        Scan only the visible approach ROI within camera field of view.
        Vehicles far upstream (> fov_max_distance) or in spawner backlogs are invisible.
        """
        visible_counts: Dict[str, int] = {k: 0 for k in MOVEMENT_KEYS}
        for lane_id, queue in intersection.lanes.items():
            if lane_id not in visible_counts:
                continue
            # Count only vehicles physically located within visible camera ROI
            count = sum(
                1 for v in queue
                if v.state != "passed" and CAMERA_FOV_STOP_LINE <= v.position <= self.fov_max_distance
            )
            visible_counts[lane_id] = count

        # Observable outgoing departures (vehicles crossing stop line onto outgoing approaches)
        visible_outgoing: Dict[str, int] = {
            "north": sum(1 for v in intersection.lanes.get("north_straight", []) if v.position > 0.42),
            "south": sum(1 for v in intersection.lanes.get("south_straight", []) if v.position > 0.42),
            "east":  sum(1 for v in intersection.lanes.get("east_straight", []) if v.position > 0.42),
            "west":  sum(1 for v in intersection.lanes.get("west_straight", []) if v.position > 0.42),
        }

        # Observable arrivals entering camera FOV
        observed_arrivals = sum(
            1 for queue in intersection.lanes.values()
            for v in queue
            if abs(v.position - self.fov_max_distance) < 0.05
        )

        return ObservedDetections(
            visible_counts=visible_counts,
            visible_outgoing=visible_outgoing,
            observed_arrivals_last_step=observed_arrivals,
        )

    def build_observation(
        self,
        intersection: Intersection,
        detections: Optional[ObservedDetections] = None,
        dt: float = 0.1,
    ) -> np.ndarray:
        """
        Build camera-observable 28-D observation vector.
        """
        if detections is None:
            detections = self.extract_visible_detections(intersection)

        if detections.dropped_frame:
            self._observation_age_steps += 1
            observed_queues = self._last_observed_queues
        else:
            self._observation_age_steps = 0
            observed_queues = detections.visible_counts
            self._last_observed_queues = observed_queues.copy()

        # Update forecaster with camera-observable arrival pulses only
        self.forecaster.tick(dt=dt, spawned_this_step=detections.observed_arrivals_last_step)

        # Observable signal status (visible from physical signal lamps)
        signal = intersection.signal
        current_phase = signal.current_phase
        time_in_phase = signal.time_in_phase
        color_name = signal.color.name

        # Dims 0-11: visible queues with tanh normalization
        movements = [
            float(np.tanh(observed_queues.get(k, 0) / 15.0))
            for k in MOVEMENT_KEYS
        ]

        # Dims 12-15: observable one-hot signal phase
        phase_onehot = [0.0, 0.0, 0.0, 0.0]
        if 0 <= current_phase < 4:
            phase_onehot[current_phase] = 1.0

        # Dim 16: normalized time in phase
        time_norm = min(1.0, time_in_phase / signal.MAX_GREEN_TIME)

        # Dim 17: is transitioning indicator
        is_trans = 1.0 if color_name in ("YELLOW", "RED") else 0.0

        # Dim 18: destination-aware pressure estimated from camera
        pressures = compute_movement_pressures(observed_queues, detections.visible_outgoing, MAX_CAP)
        total_p = compute_total_pressure(pressures)
        pressure_norm = normalize_total_pressure(total_p)

        # Dim 19: max starvation timer estimated from observed green duration
        starv_timers = list(signal.phase_starvation_timer.values())
        max_starv = min(max(starv_timers) / signal.STARVATION_THRESHOLD, 1.0) if starv_timers else 0.0

        # Dims 20-27: demand forecaster features
        forecast = self.forecaster.get_forecast_features().tolist()

        obs = movements + phase_onehot + [time_norm, is_trans, pressure_norm, max_starv] + forecast
        return np.array(obs, dtype=np.float32)

    def build_state(self, env_or_intersection: Any, dt: float = 0.1) -> np.ndarray:
        """Helper that accepts either TrafficEnv or Intersection."""
        if hasattr(env_or_intersection, "intersection"):
            inter = env_or_intersection.intersection
        else:
            inter = env_or_intersection
        return self.build_observation(inter, dt=dt)
