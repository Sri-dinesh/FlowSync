import pytest
from app.realworld.digital_twin.session_recorder import SessionRecorder
from app.realworld.models.schemas import CCTVFrame, LaneCounts, VehicleArrivalEvent
from app.simulation.intersection import Intersection
from app.simulation.vehicle import Vehicle, DEFAULT_SPEED


def test_session_recorder_arrival_logging(tmp_path):
    recorder = SessionRecorder(session_id="test_sess_01", output_dir=str(tmp_path))

    arrivals = [
        {"vehicle_id": "cctv_1", "time_s": 0.5, "lane": "north", "turn": "straight", "vehicle_type": "car"},
        {"vehicle_id": "cctv_2", "time_s": 1.5, "lane": "south", "turn": "straight", "vehicle_type": "truck"},
        {"vehicle_id": "cctv_3", "time_s": 3.0, "lane": "east", "turn": "left", "vehicle_type": "bus"},
    ]
    recorder.set_arrivals(arrivals)

    twin_data = recorder.get_twin_data()
    assert twin_data["session_id"] == "test_sess_01"
    assert twin_data["total_vehicles_detected"] == 3
    assert len(twin_data["arrivals"]) == 3
    assert twin_data["arrivals"][0]["vehicle_id"] == "cctv_1"
    assert twin_data["arrivals"][1]["time_s"] == 1.5
    assert twin_data["arrivals"][2]["lane"] == "east"


def test_session_recorder_fallback_synthesis(tmp_path):
    recorder = SessionRecorder(session_id="test_synth_01", output_dir=str(tmp_path))
    
    frame = CCTVFrame(frame_id=1, timestamp_ms=1000)
    recorder.record_frame(frame)
    recorder.record_frame(frame)

    twin_data = recorder.get_twin_data()
    assert len(twin_data["arrivals"]) >= 12
    assert all("time_s" in a and "lane" in a and "turn" in a for a in twin_data["arrivals"])
    times = [a["time_s"] for a in twin_data["arrivals"]]
    assert times == sorted(times)


def test_chronological_spawning_and_clearance():
    intersection = Intersection()
    intersection.reset()
    intersection.spawner.set_enabled(False)

    arrivals = [
        {"vehicle_id": "veh_1", "time_s": 0.2, "lane": "north", "turn": "straight", "vehicle_type": "car"},
        {"vehicle_id": "veh_2", "time_s": 0.4, "lane": "south", "turn": "straight", "vehicle_type": "car"},
        {"vehicle_id": "veh_3", "time_s": 0.6, "lane": "north", "turn": "straight", "vehicle_type": "car"},
    ]

    pending = list(arrivals)
    total_vehicles = len(arrivals)
    spawned_count = 0
    sim_time = 0.0
    TICK_DT = 0.1

    for _ in range(300):
        if intersection.total_passed >= total_vehicles and len(pending) == 0:
            break

        sim_time += TICK_DT

        while pending and pending[0]["time_s"] <= sim_time:
            arr = pending.pop(0)
            lane_key = f"{arr['lane']}_{arr['turn']}"
            v = Vehicle(
                id=arr["vehicle_id"],
                lane=arr["lane"],
                turn=arr["turn"],
                position=0.0,
                wait_time=0.0,
                speed=DEFAULT_SPEED,
                state="waiting",
            )
            intersection.lanes[lane_key].append(v)
            spawned_count += 1

        intersection.tick(dt=TICK_DT, action=0)

    assert spawned_count == 3
    assert intersection.total_passed == 3
    assert intersection.get_total_waiting() == 0
    assert sim_time > 0.0
