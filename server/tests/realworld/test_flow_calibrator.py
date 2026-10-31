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

    with pytest.raises(ValueError, match="observation_window"):
        calibrator.calibrate_from_session(str(session_file))


def event_session():
    return dict(session_id="supplied",observation_window=dict(start_s=0.,end_s=60.,timebase="synthetic_seconds"),
        arrivals=[dict(vehicle_id="n1",lane="north",turn="straight",time_s=1.,event_semantics="upstream_demand_arrival"),
                  dict(vehicle_id="e1",lane="east",turn="left",time_s=30.,event_semantics="upstream_demand_arrival")])


def test_event_rates_do_not_depend_on_occupancy_sampling_frequency(tmp_path):
    from hashlib import sha256
    calibrator = FlowCalibrator()
    data = event_session()
    path = tmp_path/"events.json"
    path.write_text(json.dumps(data))
    first = calibrator.calibrate_from_session(str(path))
    assert first.spawn_rates["north_straight"] == 1. and first.avg_vehicles_per_minute == 2.
    assert first.turn_ratios["east"]["left"] == 1. and "south" not in first.turn_ratios
    assert first.vehicle_type_distribution == {} and first.peak_hours == []
    assert first.calibration_provenance.source_file_sha256 == sha256(path.read_bytes()).hexdigest()
    data["frames"] = [dict(timestamp_ms=t*1000,raw_counts=dict(north_straight=100)) for t in range(60)]
    path.write_text(json.dumps(data))
    second = calibrator.calibrate_from_session(str(path))
    assert first.spawn_rates == second.spawn_rates and first.turn_ratios == second.turn_ratios
    assert second.calibration_provenance.measurement_validation == "not_independently_validated"


@pytest.mark.parametrize("mutation",["sighting","discharge","duplicate","outside","nan","clock","empty"])
def test_invalid_event_calibration_is_rejected(tmp_path,mutation):
    data = event_session()
    if mutation == "sighting": data["arrivals"][0]["event_semantics"] = "first_track_sighting_not_stop_line_arrival"
    elif mutation == "discharge": data["arrivals"][0]["event_semantics"] = "inferred_stop_line_discharge"
    elif mutation == "duplicate": data["arrivals"][1]["vehicle_id"] = "n1"
    elif mutation == "outside": data["arrivals"][1]["time_s"] = 60.
    elif mutation == "nan": data["observation_window"]["end_s"] = float("nan")
    elif mutation == "clock": data["observation_window"]["timebase"] = "unknown"
    else: data["arrivals"] = []
    path = tmp_path/"invalid.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        FlowCalibrator().calibrate_from_session(str(path))
