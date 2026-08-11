"""
Unit tests for FlowCalibrator in app/realworld/digital_twin/flow_calibrator.py
"""
import json
import pytest
from app.realworld.digital_twin.flow_calibrator import FlowCalibrator
from app.realworld.models.schemas import CCTVFrame, LaneCounts


def test_flow_calibrator_compute_params(tmp_path):
    calibrator = FlowCalibrator()

    # Create dummy CCTV frames across 2 minutes
    frames = []
    for t_sec in range(0, 120, 10):
        frame = CCTVFrame(
            frame_id=len(frames) + 1,
            timestamp_ms=float(t_sec * 1000),
            raw_counts=LaneCounts(north_straight=2, east_left=1),
        )
        frames.append(frame)

    session_data = {
        "session_id": "test_session",
        "frames": [f.model_dump(mode="json") for f in frames],
    }

    session_file = tmp_path / "session_test.json"
    with open(session_file, "w") as f:
        json.dump(session_data, f)

    params = calibrator.calibrate_from_session(str(session_file))

    assert params.intersection_id == "test_session"
    assert "north_straight" in params.spawn_rates
    assert params.avg_vehicles_per_minute >= 0.0
