"""
twin_calibrator.py — Digital-Twin Calibration and Versioned Profiles
====================================================================
Task F2: Calibrates microscopic simulation arrival rates, turning splits,
and headway parameters against real-world CCTV detection logs.

Acceptance Criteria:
- Approach flow error <= 10–15%
- Turning-share error <= 10 percentage points
- Calibration profiles are versioned and stored as immutable JSON artifacts.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class ApproachCalibration:
    approach: str
    observed_arrival_rate_veh_min: float
    simulated_arrival_rate_veh_min: float
    flow_error_pct: float
    turn_ratios_observed: Dict[str, float]
    turn_ratios_simulated: Dict[str, float]
    turn_ratio_max_error_pts: float


@dataclass
class TwinCalibrationProfile:
    """Versioned digital twin calibration artifact."""
    calibration_version: str = "v1.0"
    camera_id: str = "cctv_approach_01"
    approach: str = "4_way_intersection"
    free_flow_speed: float = 12.8  # m/s (~46 km/h)
    saturation_headway: float = 2.1  # seconds
    lane_storage_capacity: int = 15  # vehicles per lane
    overall_flow_error_pct: float = 0.0
    overall_turn_error_pts: float = 0.0
    is_calibrated: bool = True
    approaches: Dict[str, ApproachCalibration] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "calibration_version": self.calibration_version,
            "camera_id": self.camera_id,
            "approach": self.approach,
            "free_flow_speed": self.free_flow_speed,
            "saturation_headway": self.saturation_headway,
            "lane_storage_capacity": self.lane_storage_capacity,
            "overall_flow_error_pct": round(self.overall_flow_error_pct, 2),
            "overall_turn_error_pts": round(self.overall_turn_error_pts, 2),
            "is_calibrated": self.is_calibrated,
            "approaches": {k: asdict(v) for k, v in self.approaches.items()},
        }

    def save(self, path: Path | str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")


class DigitalTwinCalibrator:
    """
    Computes sim-to-real flow calibration errors and creates versioned profiles.
    """

    def calibrate(
        self,
        real_sessions_data: Dict[str, Any],
        simulated_data: Dict[str, Any],
        version: str = "v1.0",
        camera_id: str = "cctv_main_01",
    ) -> TwinCalibrationProfile:
        """
        Compare empirical real-world counts against simulated parameters.
        """
        approaches = ["north", "south", "east", "west"]
        approach_cals: Dict[str, ApproachCalibration] = {}
        flow_errors = []
        turn_errors = []

        real_counts = real_sessions_data.get("aggregate_counts", {})
        sim_counts = simulated_data.get("aggregate_counts", {})
        duration_min = max(0.1, real_sessions_data.get("duration_s", 120.0) / 60.0)

        for d in approaches:
            # Sum straight, left, right for this approach
            real_s = real_counts.get(f"{d}_straight", 0)
            real_l = real_counts.get(f"{d}_left", 0)
            real_r = real_counts.get(f"{d}_right", 0)
            total_real = real_s + real_l + real_r
            real_rate = total_real / duration_min

            sim_s = sim_counts.get(f"{d}_straight", 0)
            sim_l = sim_counts.get(f"{d}_left", 0)
            sim_r = sim_counts.get(f"{d}_right", 0)
            total_sim = sim_s + sim_l + sim_r
            sim_rate = total_sim / duration_min

            # Flow error percentage
            flow_err = abs(sim_rate - real_rate) / max(0.1, real_rate) * 100.0
            flow_errors.append(flow_err)

            # Turn ratio error points
            r_turn = {
                "straight": real_s / max(1, total_real),
                "left": real_l / max(1, total_real),
                "right": real_r / max(1, total_real),
            }
            s_turn = {
                "straight": sim_s / max(1, total_sim),
                "left": sim_l / max(1, total_sim),
                "right": sim_r / max(1, total_sim),
            }
            max_turn_err = max(abs(r_turn[t] - s_turn[t]) * 100.0 for t in ["straight", "left", "right"])
            turn_errors.append(max_turn_err)

            approach_cals[d] = ApproachCalibration(
                approach=d,
                observed_arrival_rate_veh_min=round(real_rate, 2),
                simulated_arrival_rate_veh_min=round(sim_rate, 2),
                flow_error_pct=round(flow_err, 2),
                turn_ratios_observed={k: round(v, 3) for k, v in r_turn.items()},
                turn_ratios_simulated={k: round(v, 3) for k, v in s_turn.items()},
                turn_ratio_max_error_pts=round(max_turn_err, 2),
            )

        overall_flow = float(np.mean(flow_errors))
        overall_turn = float(np.mean(turn_errors))

        # Tolerances: flow <= 15%, turn <= 10 percentage points
        is_cal = (overall_flow <= 15.0 and overall_turn <= 10.0)

        profile = TwinCalibrationProfile(
            calibration_version=version,
            camera_id=camera_id,
            approach="4_way_intersection",
            free_flow_speed=12.8,
            saturation_headway=2.1,
            lane_storage_capacity=15,
            overall_flow_error_pct=overall_flow,
            overall_turn_error_pts=overall_turn,
            is_calibrated=is_cal,
            approaches=approach_cals,
        )
        return profile
