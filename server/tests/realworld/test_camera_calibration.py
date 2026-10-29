import json
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi import FastAPI, WebSocketDisconnect
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.realworld.models.calibration import CameraCalibration
from app.realworld.models.schemas import BoundingBox, VehicleDetection, VideoMetadata
from app.realworld.pipeline.camera_geometry import assign_approaches, draw_calibration
from app.realworld.pipeline.cctv_pipeline import CCTVPipeline
from app.realworld.digital_twin.session_recorder import SessionRecorder
from app.routers.cctv import router
from app.websockets import cctv_ws


def configuration(source="fixture.mp4"):
    return dict(camera_id="test_camera", source=source, frame_width=1000, frame_height=1000,
                approaches=[dict(approach="north", vertices=[[.1, .1], [.4, .1], [.4, .6], [.1, .6]],
                                 stop_line=[[.1, .6], [.4, .6]]),
                            dict(approach="east", vertices=[[.4, .1], [.7, .1], [.7, .6], [.4, .6]],
                                 stop_line=[[.4, .6], [.7, .6]])])


def detection(width=1000):
    boxes = [BoundingBox(x1=x-5, x2=x+5, y1=y-10, y2=y, confidence=.99, class_id=2, class_name="car")
             for x, y in ((200, 400), (600, 400), (400, 300), (200, 700), (900, 800))]
    return VehicleDetection(frame_id=1, timestamp_ms=0, bboxes=boxes, frame_width=width, frame_height=1000)


def test_exclusive_approaches_shared_boundary_abstention_and_downstream_exclusion():
    calibration = CameraCalibration.model_validate(configuration())
    assignments, result = assign_approaches(detection(), calibration)
    assert assignments == ["north", "east", None, None, None]
    assert result.approach_counts == {"north": 1, "east": 1}
    assert (result.assigned_boxes, result.unassigned_boxes, result.ambiguous_boxes) == (2, 3, 1)
    reverse = configuration()
    reverse["approaches"].reverse()
    assert assign_approaches(detection(), CameraCalibration.model_validate(reverse))[0] == assignments


@pytest.mark.parametrize("fault", ["overlap", "duplicate", "concave", "crossed", "collinear", "outside", "nan", "line_inside", "line_point", "duplicate_vertex"])
def test_invalid_geometry_rejected_at_parse(fault):
    value = configuration()
    region = value["approaches"][0]
    if fault == "overlap":
        value["approaches"][1] = {**region, "approach": "east"}
    elif fault == "duplicate":
        value["approaches"][1]["approach"] = "north"
    elif fault == "concave":
        region["vertices"] = [[.1, .1], [.4, .1], [.2, .3], [.4, .6], [.1, .6]]
    elif fault == "crossed":
        region["vertices"][1], region["vertices"][2] = region["vertices"][2], region["vertices"][1]
    elif fault == "collinear":
        region["vertices"] = [[.1, .1], [.2, .2], [.3, .3]]
    elif fault == "outside":
        region["vertices"][0] = [-.1, .1]
    elif fault == "nan":
        region["vertices"][0] = [float("nan"), .1]
    elif fault == "line_inside":
        region["stop_line"] = [[.2, .3], [.3, .3]]
    elif fault == "line_point":
        region["stop_line"][1] = region["stop_line"][0]
    else:
        region["vertices"].append(region["vertices"][0])
    with pytest.raises(ValidationError):
        CameraCalibration.model_validate(value)


def test_clockwise_regions_and_partial_stop_line_are_valid():
    value = configuration()
    value["approaches"][0]["vertices"].reverse()
    value["approaches"][0]["stop_line"] = [[.15, .6], [.35, .6]]
    assert assign_approaches(detection(), CameraCalibration.model_validate(value))[0][0] == "north"


@pytest.mark.parametrize("fault", ["frame_size_mismatch", "detector_unavailable"])
def test_unusable_frame_never_falls_back_to_image_guesses(fault):
    frame = detection(900 if fault == "frame_size_mismatch" else 1000)
    frame.model_not_loaded = fault == "detector_unavailable"
    assignments, result = assign_approaches(frame, CameraCalibration.model_validate(configuration()))
    assert assignments == [None]*5
    assert result.status == fault and result.assigned_boxes == 0 and result.unassigned_boxes == 5


def test_calibration_http_validation_and_roundtrip_hash():
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        response = client.post("/cctv/calibration/validate", json=configuration())
        assert response.status_code == 200
        data = response.json()
        parsed = CameraCalibration.model_validate_json(data["calibration_json"])
        assert parsed.sha256 == data["sha256"]
        invalid = configuration()
        invalid["frame_width"] = 0
        assert client.post("/cctv/calibration/validate", json=invalid).status_code == 422


@pytest.mark.asyncio
async def test_pipeline_and_recording_use_configured_counts_without_turn_or_replay_claim(tmp_path):
    calibration = CameraCalibration.model_validate(configuration())
    frames = []
    async def read_frame():
        return np.zeros((1000, 1000, 3), dtype=np.uint8)
    async def detect(_):
        return detection()
    async def emit(frame):
        frames.append(frame)
    pipeline = CCTVPipeline(SimpleNamespace(read_frame=read_frame, is_live=False, source_time_s=0.), SimpleNamespace(detect=detect),
                            emit, calibration=calibration, annotate_frames=True)
    await pipeline._tick()
    frame = frames[-1]
    assert frame.raw_counts.total() == 2
    assert frame.geometry_observation.approach_counts == {"north": 1, "east": 1}
    assert frame.observation_contract.count_semantics == "configured_approach_region"
    assert not frame.observation_contract.movement_counts_available
    assert frame.signal_phase is None and frame.annotated_frame_b64
    assert all(event["turn"] is None and event["calibration_sha256"] == calibration.sha256 for event in pipeline.arrival_events)
    recorder = SessionRecorder("test", str(tmp_path), calibration=calibration)
    recorder.record_frame(frame)
    recorder.set_arrivals(pipeline.arrival_events)
    assert not recorder.get_twin_data()["replay_inputs_complete"]
    saved = json.loads(open(recorder.save()).read())
    assert CameraCalibration.model_validate(saved["calibration"]).sha256 == saved["calibration_sha256"]
    # A changed frame size after valid occupancy must not retain last-good values.
    async def changed_detection(_):
        return detection(900)
    pipeline.yolo_detector.detect = changed_detection
    await pipeline._tick()
    assert frames[-1].raw_counts.total() == frames[-1].weighted_counts.total() == 0
    assert frames[-1].geometry_observation.status == "frame_size_mismatch"


def test_overlay_draws_stop_line_without_mutating_source_frame():
    calibration = CameraCalibration.model_validate(configuration())
    frame = np.zeros((1000, 1000, 3), dtype=np.uint8)
    output = draw_calibration(frame, calibration)
    assert not frame.any()
    assert output[600, 200].any()


@pytest.mark.asyncio
async def test_websocket_rejects_wrong_source_before_opening_video(monkeypatch):
    sent = []
    class Socket:
        async def accept(self):
            pass
        async def receive_text(self):
            if sent:
                raise WebSocketDisconnect()
            return json.dumps({"command": "start_processing", "payload": {
                "video_path": "different.mp4", "calibration_json": json.dumps(configuration())}})
        async def send_json(self, data):
            sent.append(data)
    def forbidden_open(*args):
        pytest.fail("Invalid calibration must not open a source")
    monkeypatch.setattr(cctv_ws, "VideoProcessor", forbidden_open)
    await cctv_ws.cctv_socket(Socket())
    assert sent[0]["code"] == "INVALID_CALIBRATION"


@pytest.mark.asyncio
async def test_websocket_rejects_wrong_dimensions_and_closes_candidate(monkeypatch, tmp_path):
    source = tmp_path / "clip.mp4"
    source.touch()
    sent, closed = [], []
    class Video:
        def __init__(self, source):
            pass
        async def open(self):
            return VideoMetadata(width=640, height=480, source_fps=25, target_fps=2)
        async def close(self):
            closed.append(True)
    class Socket:
        async def accept(self):
            pass
        async def receive_text(self):
            if sent:
                raise WebSocketDisconnect()
            return json.dumps({"command": "start_processing", "payload": {
                "video_path": str(source), "calibration_json": json.dumps(configuration(str(source)))}})
        async def send_json(self, data):
            sent.append(data)
    monkeypatch.setattr(cctv_ws, "VideoProcessor", Video)
    await cctv_ws.cctv_socket(Socket())
    assert sent[0]["code"] == "SOURCE_CONFIGURATION_FAILED" and closed == [True]
