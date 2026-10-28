import itertools
from types import SimpleNamespace

import numpy as np
import pytest

from app.realworld.digital_twin.arrival_contract import replay_input_error
from app.realworld.digital_twin.session_recorder import SessionRecorder
from app.realworld.models.schemas import BoundingBox, CCTVFrame, VehicleDetection
from app.realworld.pipeline.cctv_pipeline import CCTVPipeline
from app.realworld.pipeline.quadrant_counter import QuadrantCounter, image_direction
from app.websockets.simulation_ws import _run_timed_benchmark
from app.websockets import simulation_ws
from fastapi import WebSocketDisconnect


def box(x, y):
    return BoundingBox(x1=x-5, x2=x+5, y1=y-10, y2=y, confidence=.99, class_id=2, class_name="car")


def detection(boxes):
    return VehicleDetection(frame_id=1, timestamp_ms=0, bboxes=boxes, frame_width=1000, frame_height=1000)


def test_each_detection_has_at_most_one_image_direction_and_ties_are_unassigned():
    counter = QuadrantCounter()
    all_boxes = [box(x, y) for x, y in itertools.product(range(50, 1000, 50), repeat=2)]
    totals = [sum(counter.count(detection([b])).values()) for b in all_boxes]
    assert set(totals) == {0, 1}
    assert sum(totals) == 324
    assert sum(counter.count(detection(all_boxes)).values()) == sum(totals)
    assert image_direction(box(500, 500), 1000, 1000) is None
    assert image_direction(box(500, 100), 1000, 1000) == "north"
    assert image_direction(box(900, 500), 1000, 1000) == "east"


def test_invalid_geometry_is_not_counted_and_missing_detector_is_not_a_measurement():
    counter = QuadrantCounter()
    for b in (box(-10, 100), box(100, float("nan")), box(100, 1100)):
        assert sum(counter.count(detection([b])).values()) == 0
    frame = detection([box(500, 100)])
    frame.model_not_loaded = True
    assert sum(counter.count(frame).values()) == 0
    with pytest.raises(ValueError, match="dimensions"):
        image_direction(box(500, 100), 0, 1000)


def test_unknown_camera_control_outputs_are_not_zero_or_a_default_green():
    frame = CCTVFrame(frame_id=0, timestamp_ms=0)
    assert frame.signal_phase is None and frame.signal_phase_name is None
    assert frame.estimated_avg_wait is None and frame.confidence_pct is None
    assert frame.observation == frame.q_values == []
    assert not frame.observation_contract.physical_actuation
    assert frame.observation_contract.control_status == "unavailable"


@pytest.mark.asyncio
async def test_actual_pipeline_emits_conserved_counts_unknown_turns_and_no_fake_controller(tmp_path):
    outputs = []
    async def read_frame():
        return np.zeros((1000, 1000, 3), dtype=np.uint8)
    async def detect(_):
        return detection([box(500, 100), box(900, 500), box(500, 500)])
    async def on_frame(frame):
        outputs.append(frame)
    pipeline = CCTVPipeline(SimpleNamespace(read_frame=read_frame, is_live=False),
                            SimpleNamespace(detect=detect), on_frame, annotate_frames=False)
    await pipeline._tick()
    await pipeline._tick()
    frame = outputs[-1]
    assert frame.raw_counts.total() == 2
    assert frame.vehicle_types.car == 3
    contract = frame.observation_contract
    assert (contract.detected_boxes, contract.assigned_boxes, contract.unassigned_boxes) == (3, 2, 1)
    assert frame.signal_phase is None and frame.q_values == [] and frame.observation == []
    assert frame.estimated_avg_wait is None
    assert len(pipeline.arrival_events) == 2
    assert all(a["turn"] is None and a["time_source"] == "processing_cadence_proxy" for a in pipeline.arrival_events)
    recorder = SessionRecorder("contract", output_dir=str(tmp_path))
    recorder.set_arrivals(pipeline.arrival_events)
    assert not recorder.get_twin_data()["replay_inputs_complete"]


@pytest.mark.parametrize("change", [{"turn": None}, {"time_s": float("nan")}, {"time_s": -1},
                                    {"lane": "unknown"}, {"vehicle_id": ""},
                                    {"event_semantics": "first_track_sighting_not_stop_line_arrival"}])
def test_incomplete_replay_is_rejected(change):
    row = dict(vehicle_id="a", lane="north", turn="left", time_s=1.)
    assert replay_input_error([row]) is None
    assert replay_input_error([{**row, **change}])
    assert replay_input_error([row, row])


@pytest.mark.asyncio
async def test_replay_rejection_precedes_any_simulation_or_shared_state_mutation():
    sent = []
    async def send_json(value):
        sent.append(value)
    app = SimpleNamespace(state=SimpleNamespace(sim_running=True))
    await _run_timed_benchmark(app, SimpleNamespace(send_json=send_json), 60, None, ["fixed"],
                               arrivals=[dict(vehicle_id="a", lane="north", turn=None, time_s=0.)])
    assert sent[0]["type"] == "error"
    assert app.state.sim_running is True
    assert not hasattr(app.state, "benchmark_running")


@pytest.mark.asyncio
async def test_socket_rejects_empty_replay_without_cancelling_an_existing_benchmark(monkeypatch):
    sent = []
    cancellations = []
    existing_task = SimpleNamespace(cancel=lambda: cancellations.append(True))
    state = SimpleNamespace(sim_task=object(), sim_running=True,
                            benchmark_task=existing_task, benchmark_running=True,
                            benchmark_cancelled=False)
    async def accept():
        pass
    async def receive_json():
        if sent:
            raise WebSocketDisconnect()
        return {"command": "run_timed_benchmark", "arrivals": []}
    async def send_json(value):
        sent.append(value)
    manager = simulation_ws.ConnectionManager()
    # A second connected client keeps the existing simulation alive on disconnect.
    manager.active_connections.append(object())
    monkeypatch.setattr(simulation_ws, "manager", manager)
    websocket = SimpleNamespace(app=SimpleNamespace(state=state), accept=accept,
                                receive_json=receive_json, send_json=send_json)
    await simulation_ws.simulation_socket(websocket)
    assert sent[0]["type"] == "error"
    assert state.sim_running and state.benchmark_running
    assert not state.benchmark_cancelled and not cancellations
    assert state.benchmark_task is existing_task
