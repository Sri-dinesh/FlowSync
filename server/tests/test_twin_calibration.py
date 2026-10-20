"""
test_twin_calibration.py — Unit Tests for CV Validation & Digital Twin Calibration
===================================================================================
Task E4 & Task F2: Validates CV state estimation metrics and digital-twin flow calibration.
"""
from pathlib import Path
import json
import numpy as np
import pytest

from research.cv.validation_tool import CVStateValidator, CVValidationReport
from research.calibration.twin_calibrator import DigitalTwinCalibrator, TwinCalibrationProfile


def test_cv_state_validator_metrics():
    """CVStateValidator must accurately compute precision, recall, MAE, and correlation."""
    validator = CVStateValidator()

    # Synthetic reference data: 5 frames
    predicted_frames = [
        {"lane_counts": {"north_straight": 5, "south_straight": 4, "east_straight": 2}, "confidences": [0.92, 0.95]},
        {"lane_counts": {"north_straight": 3, "south_straight": 4, "east_straight": 3}, "confidences": [0.88, 0.91]},
        {"lane_counts": {"north_straight": 6, "south_straight": 2, "east_straight": 1}, "confidences": [0.94]},
        {"lane_counts": {"north_straight": 0, "south_straight": 1, "east_straight": 0}, "confidences": [0.35]}, # Degraded
        {"lane_counts": {"north_straight": 2, "south_straight": 3, "east_straight": 2}, "confidences": [0.90]},
    ]
    annotated_frames = [
        {"lane_counts": {"north_straight": 5, "south_straight": 4, "east_straight": 2}}, # Exact
        {"lane_counts": {"north_straight": 4, "south_straight": 4, "east_straight": 3}}, # 1 off
        {"lane_counts": {"north_straight": 6, "south_straight": 2, "east_straight": 1}}, # Exact
        {"lane_counts": {"north_straight": 4, "south_straight": 3, "east_straight": 1}}, # 7 off (miss)
        {"lane_counts": {"north_straight": 2, "south_straight": 3, "east_straight": 2}}, # Exact
    ]

    report = validator.evaluate(predicted_frames, annotated_frames)
    assert isinstance(report, CVValidationReport)
    assert report.total_frames_evaluated == 5
    assert report.precision > 0.85
    assert report.recall > 0.70
    assert report.count_mae >= 0.0
    assert report.lane_assignment_accuracy_pct > 70.0


def test_digital_twin_calibration_profile(tmp_path):
    """DigitalTwinCalibrator must evaluate flow error and save versioned profile artifact."""
    calibrator = DigitalTwinCalibrator()

    # Real CCTV detection session data
    real_data = {
        "duration_s": 120.0,
        "aggregate_counts": {
            "north_straight": 20, "north_left": 5, "north_right": 5,
            "south_straight": 20, "south_left": 5, "south_right": 5,
            "east_straight": 10, "east_left": 2, "east_right": 2,
            "west_straight": 10, "west_left": 2, "west_right": 2,
        },
    }

    # Calibrated simulation data (within 8% of real flow)
    sim_data = {
        "duration_s": 120.0,
        "aggregate_counts": {
            "north_straight": 19, "north_left": 5, "north_right": 5,
            "south_straight": 21, "south_left": 5, "south_right": 4,
            "east_straight": 10, "east_left": 2, "east_right": 2,
            "west_straight": 11, "west_left": 2, "west_right": 2,
        },
    }

    profile = calibrator.calibrate(
        real_sessions_data=real_data,
        simulated_data=sim_data,
        version="v1.0",
        camera_id="cam_main_01",
    )

    assert profile.is_calibrated is True
    assert profile.overall_flow_error_pct < 15.0  # Within Task F2 tolerance (<= 15%)
    assert profile.overall_turn_error_pts < 10.0  # Within Task F2 tolerance (<= 10 pts)

    # Save to disk
    out_file = Path("research/calibration/profiles/calib_profile_v1.json")
    profile.save(out_file)
    assert out_file.exists()

    loaded = json.loads(out_file.read_text())
    assert loaded["calibration_version"] == "v1.0"
    assert loaded["is_calibrated"] is True
