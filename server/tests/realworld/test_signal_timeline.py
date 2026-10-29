import json
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi import FastAPI, WebSocketDisconnect
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.realworld.models.signal_timeline import SignalTimeline, SignalTimelineReader
from app.realworld.models.schemas import VehicleDetection, VideoMetadata
from app.realworld.pipeline.cctv_pipeline import CCTVPipeline
from app.realworld.digital_twin.session_recorder import SessionRecorder
from app.routers.cctv import router
from app.websockets import cctv_ws

VIDEO_HASH = "a"*64


def timeline_data():
    return dict(schema_version="recorded_signal_v1", video_sha256=VIDEO_HASH,
        origin="synthetic_fixture",annotation_method="Explicit test intervals; not real signal observations.",time_resolution_s=.1,
        segments=[dict(start_s=0,end_s=1,state="green",phase=0,onset_observed=False),
                  dict(start_s=1,end_s=1.5,state="yellow",phase=0,onset_observed=True),
                  dict(start_s=1.5,end_s=2,state="all_red",onset_observed=True),
                  dict(start_s=2,end_s=3,state="green",phase=1,onset_observed=True),
                  dict(start_s=4,end_s=5,state="unknown")])


def test_half_open_boundaries_clearance_and_partial_green_onset():
    reader=SignalTimelineReader(SignalTimeline.model_validate(timeline_data()))
    first=reader.at(.5,VIDEO_HASH)
    assert first.status=="available" and first.phase==0 and first.green_elapsed_s is None
    assert reader.at(1,VIDEO_HASH).state=="yellow"
    assert reader.at(1.5,VIDEO_HASH).state=="all_red"
    assert reader.at(1.5,VIDEO_HASH).phase is None
    green=reader.at(2.25,VIDEO_HASH)
    assert green.phase==1 and green.green_elapsed_s==.25
    assert reader.at(3,VIDEO_HASH).status=="gap"
    assert reader.at(4,VIDEO_HASH).status=="unknown"
    assert reader.at(5,VIDEO_HASH).status=="gap"


@pytest.mark.parametrize("time",[None,float("nan"),float("inf"),-1])
def test_missing_or_invalid_time_never_creates_signal_state(time):
    observed=SignalTimelineReader(SignalTimeline.model_validate(timeline_data())).at(time,VIDEO_HASH)
    assert observed.status=="source_timing_unavailable" and observed.phase is None
    assert observed.source_time_s is None


def test_wrong_video_never_supplies_observed_phase():
    observed=SignalTimelineReader(SignalTimeline.model_validate(timeline_data())).at(.5,"b"*64)
    assert observed.status=="video_mismatch" and observed.state is None


@pytest.mark.parametrize("fault",["overlap","unsorted","zero_duration","unknown_phase","all_red_phase","missing_phase","bool_phase","nan","fake_unknown_onset","duplicate_state","hash"])
def test_malformed_timelines_rejected(fault):
    data=timeline_data()
    if fault=="overlap": data["segments"][1]["start_s"]=.5
    elif fault=="unsorted": data["segments"].reverse()
    elif fault=="zero_duration": data["segments"][0]["end_s"]=0
    elif fault=="unknown_phase": data["segments"][0]["phase"]=7
    elif fault=="all_red_phase": data["segments"][2]["phase"]=0
    elif fault=="missing_phase": del data["segments"][0]["phase"]
    elif fault=="bool_phase": data["segments"][0]["phase"]=True
    elif fault=="nan": data["segments"][0]["start_s"]=float("nan")
    elif fault=="fake_unknown_onset": data["segments"][-1]["onset_observed"]=True
    elif fault=="duplicate_state": data["segments"][1].update(state="green",phase=0)
    else: data["video_sha256"]="not-a-hash"
    with pytest.raises(ValidationError): SignalTimeline.model_validate(data)


def test_validation_api_roundtrips_exact_timeline_identity():
    app=FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        response=client.post("/cctv/signal-timeline/validate",json=timeline_data())
        assert response.status_code==200
        result=response.json()
        assert SignalTimeline.model_validate_json(result["signal_timeline_json"]).sha256==result["sha256"]


@pytest.mark.asyncio
async def test_pipeline_preserves_recorded_observation_separately_from_control(tmp_path):
    timeline=SignalTimeline.model_validate(timeline_data())
    frames=[]
    async def read_frame(): return np.zeros((100,100,3),dtype=np.uint8)
    async def detect(_): return VehicleDetection(frame_id=0,timestamp_ms=0,frame_width=100,frame_height=100,bboxes=[])
    async def emit(frame): frames.append(frame)
    video=SimpleNamespace(read_frame=read_frame,is_live=False,source_time_s=2.25,source_video_sha256=VIDEO_HASH)
    pipeline=CCTVPipeline(video,SimpleNamespace(detect=detect),emit,signal_timeline=timeline,annotate_frames=False)
    await pipeline._tick()
    observed=frames[0]
    assert observed.recorded_signal.phase==1 and observed.recorded_signal.green_elapsed_s==.25
    assert observed.signal_phase is None and observed.q_values==[]
    assert observed.observation_contract.control_status=="unavailable"
    assert "Complete signal timing and phase-service history" in observed.observation_contract.missing_inputs
    recorder=SessionRecorder("test",str(tmp_path),source_video_sha256=VIDEO_HASH,signal_timeline=timeline)
    recorder.record_frame(observed)
    saved=json.loads(open(recorder.save()).read())
    assert SignalTimeline.model_validate(saved["signal_timeline"]).sha256==saved["signal_timeline_sha256"]
    assert not saved["twin_data"]["replay_inputs_complete"]
    video.source_time_s=3.5
    await pipeline._tick()
    assert frames[-1].recorded_signal.status=="gap" and frames[-1].recorded_signal.phase is None


@pytest.mark.asyncio
@pytest.mark.parametrize("live",[False,True])
async def test_socket_rejects_wrong_video_or_live_timeline_before_start(monkeypatch,tmp_path,live):
    source=tmp_path/"clip.avi"
    source.touch()
    sent,closed=[],[]
    class Video:
        source_video_sha256="b"*64
        def __init__(self,source):
            assert not live
        async def open(self): return VideoMetadata(width=100,height=100,source_fps=25,target_fps=2)
        async def close(self): closed.append(True)
    class Socket:
        async def accept(self): pass
        async def receive_text(self):
            if sent: raise WebSocketDisconnect()
            return json.dumps(dict(command="start_processing",payload=dict(
                video_path="rtsp://example.invalid/live" if live else str(source),
                signal_timeline_json=json.dumps(timeline_data()))))
        async def send_json(self,data): sent.append(data)
    monkeypatch.setattr(cctv_ws,"VideoProcessor",Video)
    await cctv_ws.cctv_socket(Socket())
    assert sent[0]["code"]==("RECORDED_VIDEO_REQUIRED" if live else "SOURCE_CONFIGURATION_FAILED")
    assert closed==([] if live else [True])
