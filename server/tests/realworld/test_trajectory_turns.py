import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from pydantic import ValidationError

from app.realworld.models.calibration import CameraCalibration
from app.realworld.pipeline.camera_geometry import assign_approaches
from app.realworld.pipeline.stop_line_crossings import StopLineCrossings
from app.realworld.pipeline.trajectory_turns import TrajectoryTurns
from app.realworld.pipeline.cctv_pipeline import CCTVPipeline
from app.realworld.pipeline.video_processor import VideoProcessor
from app.realworld.digital_twin.session_recorder import SessionRecorder
from app.realworld.digital_twin.arrival_contract import replay_input_error
from research.cv.export_trajectory_predictions import export
from research.cv.evaluate_movements import run, verify
from .test_stop_line_crossings import calibration as base_calibration, detection


def calibration(turn="straight", source="test.avi"):
    data = base_calibration(source).model_dump()
    data["exits"] = [dict(exit_id="departure", vertices=[[.1,.64],[.4,.64],[.4,.9],[.1,.9]], turns_from={"north":turn})]
    return CameraCalibration.model_validate(data)


def sequence(rows, config=None):
    config = config or calibration()
    crossing, engine = StopLineCrossings(config), TrajectoryTurns(config)
    results = []
    for frame, time, y, x, tid in rows:
        packet = detection(frame, y, x=x, tid=tid)
        assignments, geometry = assign_approaches(packet, config)
        observation = crossing.update(packet, assignments, geometry, time)
        results.append(engine.update(packet, observation))
    return results


PREFIX = [(1,0.,580,250,1),(2,.5,620,250,1)]


@pytest.mark.parametrize("turn", ["straight", "left", "right", "u_turn"])
def test_turn_requires_crossing_and_two_exit_observations_with_later_availability(turn):
    result = sequence(PREFIX+[(3,1.,650,250,1),(4,1.5,670,250,1),(5,2.,680,250,1)],calibration(turn))
    assert result[1].pending_count == 1 and result[1].classified_count == 0
    assert result[2].classified_count == 0
    event = result[3].events[0]
    assert event.turn == turn and event.available_time_s == 1.5 and event.crossing_frame_id == 2
    assert event.event_semantics == "retrospective_crossing_to_exit"
    assert result[-1].classified_count == 1 and result[-1].events == []


def test_exit_without_previous_stop_line_crossing_never_becomes_a_turn():
    results = sequence([(1,0.,650,250,1),(2,.5,670,250,1)])
    assert not results[-1].events and results[-1].classified_count == 0


@pytest.mark.parametrize("suffix, reason", [
    ([(3,1.,None,250,1)],"track_lost"),
    ([(3,1.,650,250,2)],"track_lost"),
    ([(3,2.,650,250,1)],"timing_gap"),
    ([(4,1.,650,250,1)],"timing_gap"),
    ([(3,None,650,250,1)],"observation_unavailable"),
    ([(3,-1.,650,250,1)],"observation_unavailable"),
    ([(3,.5,650,250,1)],"observation_unavailable"),
    ([(3,1.,750,250,1)],"implausible_displacement"),
])
def test_broken_evidence_remains_unresolved(suffix, reason):
    result = sequence(PREFIX+suffix)[-1]
    assert result.events[0].reason == reason and result.events[0].turn is None
    assert result.unresolved_count == 1 and result.pending_count == 0


def test_confirmation_resets_when_vehicle_leaves_exit_region():
    result = sequence(PREFIX+[(3,1.,650,250,1),(4,1.5,630,250,1),(5,2.,650,250,1),(6,2.5,660,250,1)])
    assert result[-2].classified_count == 0 and result[-1].classified_count == 1


def test_shared_exit_boundary_is_ambiguous():
    data = calibration().model_dump(mode="json")
    data["exits"][0]["vertices"] = [[.1,.64],[.25,.64],[.25,.9],[.1,.9]]
    data["exits"].append(dict(exit_id="other",vertices=[[.25,.64],[.4,.64],[.4,.9],[.25,.9]],turns_from={"north":"left"}))
    result = sequence(PREFIX+[(3,1.,650,250,1)], CameraCalibration.model_validate(data))[-1]
    assert result.events[0].reason == "ambiguous_exit" and result.events[0].turn is None


def test_unknown_exit_mapping_abstains():
    data = calibration().model_dump(mode="json")
    approach = copy.deepcopy(data["approaches"][0])
    approach.update(approach="south",vertices=[[.6,.1],[.9,.1],[.9,.6],[.6,.6]],stop_line=[[.65,.6],[.85,.6]])
    data["approaches"].append(approach)
    data["exits"][0]["turns_from"] = {"south":"left"}
    result = sequence(PREFIX+[(3,1.,650,250,1)],CameraCalibration.model_validate(data))[-1]
    assert result.events[0].reason == "unmapped_exit" and result.events[0].turn is None


def test_trajectory_timeout_does_not_guess_turn():
    result = sequence(PREFIX+[(frame,(frame-1)*.5,630,250,1) for frame in range(3,33)])[-1]
    assert result.events[0].reason == "timeout"


@pytest.mark.parametrize("fault", ["overlap", "approach_overlap", "duplicate", "unknown_approach", "concave", "turn"])
def test_invalid_exit_configuration_rejected(fault):
    data = calibration().model_dump(mode="json")
    if fault == "overlap": data["exits"].append({**data["exits"][0], "exit_id":"second"})
    elif fault == "approach_overlap": data["exits"][0]["vertices"] = [[.1,.5],[.4,.5],[.4,.9],[.1,.9]]
    elif fault == "duplicate": data["exits"] *= 2
    elif fault == "unknown_approach": data["exits"][0]["turns_from"] = {"west":"right"}
    elif fault == "concave": data["exits"][0]["vertices"] = [[.1,.64],[.4,.64],[.2,.7],[.4,.9],[.1,.9]]
    else: data["exits"][0]["turns_from"] = {"north":"north"}
    with pytest.raises(ValidationError): CameraCalibration.model_validate(data)


def test_optional_exits_preserve_old_calibration_hash():
    config = base_calibration()
    original = config.model_dump(mode="json",exclude={"exits"})
    expected = hashlib.sha256(json.dumps(original,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    assert config.sha256 == expected
    assert calibration().sha256 != expected


def test_departure_turn_cannot_become_replay_arrival_even_with_complete_fields():
    assert replay_input_error([dict(vehicle_id="track1",lane="north",turn="left",time_s=1.,
                                    event_semantics="retrospective_crossing_to_exit")])


@pytest.mark.asyncio
@pytest.mark.parametrize("processed_frames", [3,5])
async def test_decoded_video_pipeline_records_exports_and_evaluates_turn(tmp_path, processed_frames):
    source = tmp_path/"turn.avi"
    writer = cv2.VideoWriter(str(source),cv2.VideoWriter_fourcc(*"MJPG"),2,(1000,1000))
    for y in (580,620,650,670,680):
        image = np.zeros((1000,1000,3),dtype=np.uint8)
        image[y-10:y,245:255] = 255
        writer.write(image)
    writer.release()
    video = VideoProcessor(str(source))
    await video.open()
    async def detect(image):
        mask = np.all(image>180,axis=2)
        yy,xx = np.where(mask)
        return detection(0,int(yy.max()+1),x=int(round((xx.min()+xx.max()+1)/2)),tid=None)
    config = calibration("left",str(source))
    recorder = SessionRecorder("turn",str(tmp_path),calibration=config,source_video_sha256=video.source_video_sha256)
    async def emit(frame): recorder.record_frame(frame)
    pipeline = CCTVPipeline(video,SimpleNamespace(detect=detect),emit,calibration=config,annotate_frames=False)
    while len(recorder._frames)<processed_frames:
        await pipeline._tick()
    await pipeline.stop()
    recorder.set_arrivals(pipeline.arrival_events)
    session_path = recorder.save()
    raw = open(session_path,"rb").read()
    predictions = export(raw)
    complete = processed_frames == 5
    assert len(predictions.events) == 1 and predictions.events[0].turn == ("left" if complete else None)
    assert predictions.events[0].available_time_s == (1.5 if complete else 1.)
    saved = json.loads(raw)
    assert all(frame["trajectory_detection"] is not None for frame in saved["frames"])
    assert saved["stop_line_crossings"][0]["turn"] is None
    assert not saved["twin_data"]["replay_inputs_complete"]
    annotation = dict(schema_version="movement_annotations_v1",video_sha256=video.source_video_sha256,
        calibration_sha256=config.sha256,origin="synthetic_fixture",split="development",
        annotation_method="Analytic rectangle crossing and explicitly mapped synthetic exit; not real turn labels.",time_resolution_s=.5,
        windows=[dict(window_id="north",approach="north",start_s=0.,end_s=(processed_frames-1)*.5,exhaustive=True)],
        events=[dict(event_id="rectangle",approach="north",time_s=.25,turn="left")])
    for name, data in [("annotations",annotation),("protocol",dict(schema_version="crossing_evaluation_v1",protocol_id="fixture",match_tolerance_s=.01)),
                       ("predictions",predictions.model_dump(mode="json"))]:
        (tmp_path/f"{name}.json").write_text(json.dumps(data))
    report = run(Path(session_path),tmp_path/'annotations.json',tmp_path/'protocol.json',source,tmp_path/'report',tmp_path/'predictions.json')
    assert report["metrics"]["correct_known_matches"] == int(complete)
    assert verify(tmp_path/'report',source)["verified"]
    for fault in (("aggregate", "mapping", "availability") if complete else ()):
        bad = copy.deepcopy(saved)
        if fault == "aggregate": bad["trajectory_turns"] = []
        else:
            for event in (bad["trajectory_turns"][0],bad["frames"][3]["trajectory_observation"]["events"][0]):
                event["turn" if fault == "mapping" else "available_time_s"] = "right" if fault == "mapping" else .5
        with pytest.raises(ValueError): export(json.dumps(bad).encode())
    for fault in ("missing_evidence", "missing_observation", "wrong_frame", "wrong_counts", "missing_confirmation", "changed_id"):
        bad = copy.deepcopy(saved)
        if fault == "missing_evidence": bad["frames"][0]["trajectory_detection"] = None
        elif fault == "missing_observation": bad["frames"][0]["trajectory_observation"] = None
        elif fault == "wrong_frame": bad["frames"][0]["trajectory_detection"]["frame_id"] = 999
        elif fault == "wrong_counts": bad["frames"][0]["trajectory_observation"]["pending_count"] = 1
        else:
            if fault == "missing_confirmation" and not complete:
                continue  # Both input sequences still legitimately end pending.
            box = bad["frames"][2]["trajectory_detection"]["bboxes"][0]
            if fault == "changed_id": box["track_id"] = 999
            else: box.update(y1=620.,y2=630.)
        with pytest.raises(ValueError): export(json.dumps(bad).encode())
