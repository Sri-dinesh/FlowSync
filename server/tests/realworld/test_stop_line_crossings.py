import json
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from app.realworld.models.calibration import CameraCalibration
from app.realworld.models.schemas import BoundingBox, VehicleDetection
from app.realworld.pipeline.camera_geometry import assign_approaches
from app.realworld.pipeline.stop_line_crossings import StopLineCrossings
from app.realworld.pipeline.vehicle_tracker import VehicleTracker
from app.realworld.pipeline.video_processor import VideoProcessor
from app.realworld.pipeline.cctv_pipeline import CCTVPipeline
from app.realworld.digital_twin.session_recorder import SessionRecorder
from app.realworld.digital_twin.arrival_contract import replay_input_error


def calibration(source="test.avi"):
    return CameraCalibration(camera_id="test", source=source, frame_width=1000, frame_height=1000,
        approaches=[dict(approach="north", vertices=[[.1,.1],[.4,.1],[.4,.6],[.1,.6]],
                         stop_line=[[.15,.6],[.35,.6]])])


def detection(frame, y, x=250, tid=1):
    boxes = [] if y is None else [BoundingBox(x1=x-5,x2=x+5,y1=y-10,y2=y,
        confidence=.9,class_id=2,class_name="car",track_id=tid)]
    return VehicleDetection(frame_id=frame,timestamp_ms=0,bboxes=boxes,frame_width=1000,frame_height=1000)


def update(engine, frame, time, y, **kwargs):
    packet = detection(frame,y,**kwargs)
    assignments, geometry = assign_approaches(packet,engine.calibration)
    return engine.update(packet,assignments,geometry,time)


def test_forward_crossing_has_interval_interpolated_time_and_no_duplicate_after_oscillation():
    engine = StopLineCrossings(calibration())
    assert not update(engine,1,0,580).events
    result = update(engine,2,.5,620)
    assert len(result.events) == 1
    event = result.events[0]
    assert event.time_interval_s == (0,.5) and event.estimated_time_s == pytest.approx(.25)
    assert event.point == pytest.approx((.25,.6)) and event.turn is None
    assert event.event_semantics == "inferred_stop_line_discharge"
    update(engine,3,1,580)
    assert not update(engine,4,1.5,620).events
    assert engine.counts == {"north":1}
    assert result.last_event == event
    assert replay_input_error([dict(vehicle_id="a",lane="north",turn="straight",time_s=.25,
                                    event_semantics="inferred_stop_line_discharge")])


@pytest.mark.parametrize("vertical", [False,True])
def test_crossing_direction_comes_from_region_not_endpoint_order(vertical):
    data=calibration().model_dump()
    region=data["approaches"][0]
    if vertical:
        region["stop_line"] = ((.4,.5),(.4,.2))
    else:
        region["stop_line"] = tuple(reversed(region["stop_line"]))
    engine=StopLineCrossings(CameraCalibration.model_validate(data))
    if vertical:
        update(engine,1,0,300,x=380)
        result=update(engine,2,.5,300,x=420)
    else:
        update(engine,1,0,580)
        result=update(engine,2,.5,620)
    assert len(result.events)==1 and result.events[0].estimated_time_s == pytest.approx(.25)


@pytest.mark.parametrize("sequence", [
    [(1,0,620,250),(2,.5,580,250)], # reverse direction
    [(1,0,599,250),(2,.5,601,250)], # deadband jitter
    [(1,0,580,100),(2,.5,620,100)], # crosses supporting line outside finite stop line
    [(1,0,580,150),(2,.5,620,150)], # endpoint grazing
    [(1,0,580,250),(2,2,620,250)], # temporal gap
    [(1,0,580,250),(3,.5,620,250)], # skipped processed observation
    [(1,0,580,250),(2,.5,None,250),(3,1,620,250)], # occlusion
    [(1,0,580,250),(2,0,620,250)], # repeated timestamp
    [(1,1,580,250),(2,.5,620,250)], # backwards timestamp
    [(1,0,580,250),(2,None,600,250),(3,1,620,250)], # unavailable clock
    [(1,0,550,250),(2,.5,650,250)], # implausible displacement
])
def test_uncertain_or_non_forward_observations_do_not_emit(sequence):
    engine = StopLineCrossings(calibration())
    assert not [event for frame,t,y,x in sequence for event in update(engine,frame,t,y,x=x).events]


def test_neutral_band_can_bridge_within_interval_but_not_indefinitely():
    engine = StopLineCrossings(calibration())
    update(engine,1,0,590)
    update(engine,2,.5,600)
    assert len(update(engine,3,1,610).events) == 1
    engine = StopLineCrossings(calibration())
    update(engine,1,0,590)
    update(engine,2,.5,600)
    update(engine,3,1,600)
    assert not update(engine,4,1.5,610).events


def test_duplicate_identity_and_missing_detector_clear_pending_evidence():
    for fault in ("duplicate", "detector"):
        engine = StopLineCrossings(calibration())
        update(engine,1,0,580)
        packet = detection(2,600)
        if fault == "duplicate":
            packet.bboxes.append(packet.bboxes[0].model_copy())
        else:
            packet.model_not_loaded = True
        directions, geometry = assign_approaches(packet,engine.calibration)
        engine.update(packet,directions,geometry,.5)
        assert not update(engine,3,1,620).events


def test_tracker_preserves_detector_status_and_expires_before_association(monkeypatch):
    now = [10.]
    monkeypatch.setattr("app.realworld.pipeline.vehicle_tracker.time.time",lambda: now[0])
    tracker = VehicleTracker()
    first = tracker.update(detection(1,580)).bboxes[0].track_id
    now[0] += 4
    packet = detection(2,600)
    packet.model_not_loaded = True
    result = tracker.update(packet)
    assert result.model_not_loaded and result.bboxes[0].track_id != first


@pytest.mark.asyncio
async def test_decoder_clock_not_processing_cadence_and_end_to_end_recording(tmp_path):
    source = tmp_path/"motion.avi"
    writer = cv2.VideoWriter(str(source),cv2.VideoWriter_fourcc(*"MJPG"),2,(1000,1000))
    assert writer.isOpened()
    positions = [550,570,590,610,630,650]
    for y in positions:
        frame = np.zeros((1000,1000,3),np.uint8)
        cv2.rectangle(frame,(245,y-10),(255,y),(255,255,255),-1)
        writer.write(frame)
    writer.release()
    video = VideoProcessor(source)
    await video.open()
    frames=[]
    async def detect(frame):
        _, mask = cv2.threshold(frame[:,:,0],200,255,cv2.THRESH_BINARY)
        x,y,w,h = cv2.boundingRect(mask)
        return VehicleDetection(frame_id=0,timestamp_ms=0,frame_width=1000,frame_height=1000,
            bboxes=[BoundingBox(x1=x,x2=x+w-1,y1=y,y2=y+h-1,confidence=1,class_id=2,class_name="car")])
    async def emit(frame):
        frames.append(frame)
    config = calibration(str(source))
    pipeline = CCTVPipeline(video,SimpleNamespace(detect=detect),emit,calibration=config,annotate_frames=False)
    try:
        for _ in positions:
            await pipeline._tick()  # No wall-clock sleeps; source clock must still advance.
    finally:
        await video.close()
    times=[f.crossing_observation.source_time_s for f in frames]
    assert times == pytest.approx([0,.5,1,1.5,2,2.5])
    events=[e for f in frames for e in f.crossing_observation.events]
    assert len(events)==1 and events[0].estimated_time_s == pytest.approx(1.25,abs=.03)
    recorder=SessionRecorder("crossing",str(tmp_path),calibration=config,source_video_sha256=video.source_video_sha256)
    for frame in frames: recorder.record_frame(frame)
    recorder.set_arrivals(pipeline.arrival_events)
    data=json.loads(open(recorder.save()).read())
    assert len(data["stop_line_crossings"])==1
    assert not data["twin_data"]["replay_inputs_complete"]
    assert len(data["twin_data"]["stop_line_crossings"])==1
    from research.cv.evaluate_crossings import Annotations, Protocol, Session, evaluate, video_digest
    annotations=Annotations(schema_version="crossing_annotations_v1",video_sha256=video_digest(source),
        calibration_sha256=config.sha256,origin="synthetic_fixture",split="development",
        annotation_method="Crossing specified from the synthetic rectangle motion before pipeline inference.",
        time_resolution_s=.5,windows=[dict(window_id="north",approach="north",start_s=0,end_s=2.5,exhaustive=True)],
        events=[dict(event_id="fixture_crossing",approach="north",time_s=1.25)])
    protocol=Protocol(schema_version="crossing_evaluation_v1",protocol_id="fixture",match_tolerance_s=.1)
    report=evaluate(Session.model_validate(data),annotations,protocol,video_digest(source))
    assert report["metrics"]["true_positive"]==1
    assert report["metrics"]["false_positive"]==report["metrics"]["false_negative"]==0


@pytest.mark.asyncio
async def test_bad_decoder_timestamps_never_become_fps_estimates():
    class Capture:
        def read(self): return True,np.zeros((10,10,3),np.uint8)
        def get(self,prop): return next(timestamps)
    timestamps=iter([0,0,-100,float("nan"),1000])
    video=VideoProcessor("test.avi")
    video._cap=Capture()
    times=[]
    for _ in range(5):
        await video.read_frame()
        times.append(video.source_time_s)
    assert times == [0,None,None,None,1]
