"""
FlowCalibrator — Extract real traffic flow parameters from detection sessions.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from ..models.config import LANE_KEYS, SESSION_DIR
from ..models.schemas import CCTVFrame, TrafficFlowParams


class FlowCalibrator:
    """
    Analyzes saved detection session JSON files to extract:
    - Vehicle arrival rates per lane (lambda, vehicles/minute)
    - Turn ratio distributions (% straight/left/right per approach)
    - Vehicle type distribution
    - Peak hour patterns

    These parameters replace the simulation's current fixed Poisson(lambda=0.8) spawning.
    """

    def calibrate_from_session(self, session_path: str) -> TrafficFlowParams:
        """Calibrate flow parameters from a single saved session JSON."""
        with open(session_path) as f:
            data = json.load(f)
        frames = [CCTVFrame(**fr) for fr in data.get("frames", [])]
        return self._compute_params(frames, session_id=data.get("session_id", "unknown"))

    def calibrate_from_directory(self, sessions_dir: str) -> TrafficFlowParams:
        """Aggregate flow parameters across multiple sessions."""
        all_frames: List[CCTVFrame] = []
        sessions_path = Path(sessions_dir)
        for json_file in sessions_path.glob("*.json"):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                frames = [CCTVFrame(**fr) for fr in data.get("frames", [])]
                all_frames.extend(frames)
            except Exception as e:
                print(f"[FlowCalibrator] Skipping {json_file}: {e}")
        return self._compute_params(all_frames)

    def _compute_params(
        self, frames: List[CCTVFrame], session_id: str = "aggregated"
    ) -> TrafficFlowParams:
        if not frames:
            return TrafficFlowParams(intersection_id=session_id)

        # Estimate duration from timestamps
        timestamps = [f.timestamp_ms for f in frames]
        duration_min = (max(timestamps) - min(timestamps)) / 60000.0 or 1.0

        # Arrival rates per lane
        spawn_rates = self._compute_arrival_rates(frames, duration_min)

        # Turn ratios per direction
        turn_ratios = self._compute_turn_ratios(frames)

        # Vehicle type distribution
        type_dist = self._compute_type_distribution(frames)

        # Average vehicles per minute total
        total_counts = sum(
            sum(f.raw_counts.to_dict().values()) for f in frames
        )
        avg_per_min = total_counts / duration_min

        return TrafficFlowParams(
            intersection_id=session_id,
            spawn_rates=spawn_rates,
            turn_ratios=turn_ratios,
            vehicle_type_distribution=type_dist,
            avg_vehicles_per_minute=round(avg_per_min, 2),
        )

    def _compute_arrival_rates(
        self, frames: List[CCTVFrame], duration_min: float
    ) -> Dict[str, float]:
        """Counts total vehicle appearances per lane per minute."""
        totals: Dict[str, float] = {lane: 0.0 for lane in LANE_KEYS}
        for frame in frames:
            for lane, count in frame.raw_counts.to_dict().items():
                totals[lane] += count
        # Average rate per minute
        return {lane: round(total / duration_min, 3) for lane, total in totals.items()}

    def _compute_turn_ratios(
        self, frames: List[CCTVFrame]
    ) -> Dict[str, Dict[str, float]]:
        """Compute turn ratios per direction from lane queue distributions."""
        directions = ["north", "south", "east", "west"]
        turns = ["straight", "left", "right"]
        result: Dict[str, Dict[str, float]] = {}

        for direction in directions:
            totals = {}
            grand_total = 0.0
            for turn in turns:
                lane = f"{direction}_{turn}"
                lane_total = sum(f.raw_counts.to_dict().get(lane, 0) for f in frames)
                totals[turn] = float(lane_total)
                grand_total += lane_total

            if grand_total > 0:
                result[direction] = {t: round(totals[t] / grand_total, 3) for t in turns}
            else:
                result[direction] = {"straight": 0.5, "left": 0.25, "right": 0.25}

        return result

    def _compute_type_distribution(
        self, frames: List[CCTVFrame]
    ) -> Dict[str, float]:
        """Compute vehicle type distribution from detections."""
        type_keys = ["bicycle", "motorcycle", "car", "auto_rickshaw", "van", "bus", "truck"]
        totals: Dict[str, int] = {k: 0 for k in type_keys}

        for frame in frames:
            for k in type_keys:
                totals[k] += getattr(frame.vehicle_types, k, 0)

        grand = sum(totals.values())
        if grand == 0:
            return {
                "bicycle": 0.05, "motorcycle": 0.40, "car": 0.35,
                "auto_rickshaw": 0.10, "van": 0.05, "bus": 0.03, "truck": 0.02,
            }
        return {k: round(v / grand, 4) for k, v in totals.items()}

    def export_as_simulation_config(self, params: TrafficFlowParams) -> Dict:
        """Returns dict compatible with simulation's TrafficSpawner config."""
        return {
            "intersection_id": params.intersection_id,
            "spawn_rates": params.spawn_rates,
            "turn_ratios": params.turn_ratios,
            "vehicle_type_distribution": params.vehicle_type_distribution,
            "avg_vehicles_per_minute": params.avg_vehicles_per_minute,
            "time_period": params.time_period,
        }
