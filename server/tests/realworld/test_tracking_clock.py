from types import SimpleNamespace

import numpy as np
import pytest

from app.realworld.models.schemas import BoundingBox, VehicleDetection
from app.realworld.pipeline.cctv_pipeline import CCTVPipeline
from app.realworld.pipeline.vehicle_tracker import VehicleTracker
from .test_stop_line_crossings import calibration


def packet(frame=1, y=580, x=250):
    return VehicleDetection(frame_id=frame, timestamp_ms=123456., frame_width=1000, frame_height=1000,
                            bboxes=[BoundingBox(x1=x-5, x2=x+5, y1=y-10, y2=y,
                                                confidence=.9, class_id=2, class_name="car", track_id=999)])


@pytest.mark.parametrize("wall_times", [(10., 10.1), (10., 14.), (10., -100.)])
@pytest.mark.asyncio
async def test_pipeline_crossings_do_not_depend_on_processing_speed_or_wall_clock(monkeypatch, wall_times):
    frames, wall, y = [], [wall_times[0]], [580]
    video = SimpleNamespace(is_live=False, source_time_s=0.)
    async def read_frame(): return np.zeros((1000, 1000, 3), dtype=np.uint8)
    async def detect(_): return packet(y=y[0])
    async def emit(frame): frames.append(frame)
    video.read_frame = read_frame
    monkeypatch.setattr("app.realworld.pipeline.cctv_pipeline.time", SimpleNamespace(time=lambda: wall[0], monotonic=lambda: wall[0]))
    pipeline = CCTVPipeline(video, SimpleNamespace(detect=detect), emit, calibration=calibration(), annotate_frames=False)
    await pipeline._tick()
    wall[0], video.source_time_s, y[0] = wall_times[1], .5, 620
    await pipeline._tick()
    assert len(pipeline.arrival_events) == 1
    event = frames[-1].crossing_observation.events[0]
    assert event.track_id == 1
    assert event.estimated_time_s == .25 and event.time_interval_s == (0., .5)
    assert frames[-1].signal_phase is None


@pytest.mark.parametrize("invalid", [None, float("nan"), float("inf"), -1., 0., .5])
def test_missing_or_nonadvancing_time_breaks_association_without_reusing_ids(invalid):
    tracker = VehicleTracker()
    first = tracker.update(packet(), observation_time_s=.5).bboxes[0].track_id
    missing = tracker.update(packet(), observation_time_s=invalid)
    assert missing.bboxes[0].track_id is None
    assert missing.timestamp_ms == 123456. and tracker.get_active_tracks() == {}
    recovered = tracker.update(packet(), observation_time_s=1.)
    assert recovered.bboxes[0].track_id != first


@pytest.mark.parametrize("gap, retained", [(3., True), (3.001, False)])
def test_expiry_uses_elapsed_observation_time(gap, retained):
    tracker = VehicleTracker()
    first = tracker.update(packet(), observation_time_s=0.).bboxes[0].track_id
    second = tracker.update(packet(), observation_time_s=gap).bboxes[0].track_id
    assert (first == second) is retained


def test_track_age_is_in_observation_clock_not_detection_wall_timestamp():
    tracker = VehicleTracker()
    tracker.update(packet(), observation_time_s=0.)
    tracker.update(packet(), observation_time_s=.5)
    state = tracker.get_active_tracks()[1]
    assert state.first_seen_ms == 0. and state.last_seen_ms == 500.
    assert state.wait_time_seconds == .5  # Legacy sighting-age heuristic, not physical vehicle wait.


def test_session_id_allocation_and_reset_cannot_corrupt_another_tracker():
    first, second = VehicleTracker(), VehicleTracker()
    assert first.update(packet(), observation_time_s=0.).bboxes[0].track_id == 1
    assert second.update(packet(), observation_time_s=0.).bboxes[0].track_id == 1
    second.reset()
    assert first.update(packet(x=500), observation_time_s=.5).bboxes[0].track_id == 2
    assert set(first.get_active_tracks()) == {1, 2}
    assert second.update(packet(), observation_time_s=0.).bboxes[0].track_id == 2


@pytest.mark.asyncio
async def test_file_without_source_time_never_falls_back_to_processing_clock():
    frames = []
    async def read_frame(): return np.zeros((1000, 1000, 3), dtype=np.uint8)
    async def detect(_): return packet()
    async def emit(frame): frames.append(frame)
    pipeline = CCTVPipeline(SimpleNamespace(is_live=False, read_frame=read_frame, source_time_s=None),
                            SimpleNamespace(detect=detect), emit, calibration=calibration(), annotate_frames=False)
    await pipeline._tick()
    assert frames[0].raw_counts.total() == 1
    assert frames[0].crossing_observation.status == "source_timing_unavailable"
    assert pipeline.arrival_events == [] and pipeline._tracker.get_active_tracks() == {}


@pytest.mark.asyncio
async def test_live_source_uses_monotonic_receipt_clock_without_inventing_video_time(monkeypatch):
    frames, elapsed = [], [10.]
    async def read_frame(): return np.zeros((1000, 1000, 3), dtype=np.uint8)
    async def detect(_): return packet()
    async def emit(frame): frames.append(frame)
    monkeypatch.setattr("app.realworld.pipeline.cctv_pipeline.time", SimpleNamespace(time=lambda: -10., monotonic=lambda: elapsed[0]))
    pipeline = CCTVPipeline(SimpleNamespace(is_live=True, read_frame=read_frame, source_time_s=None),
                            SimpleNamespace(detect=detect), emit, calibration=calibration(), annotate_frames=False)
    await pipeline._tick()
    elapsed[0] = 10.5
    await pipeline._tick()
    assert len(pipeline.arrival_events) == 1
    assert frames[-1].crossing_observation.status == "source_timing_unavailable"
    assert pipeline._tracker.get_active_tracks()[1].last_seen_ms == 10500.
