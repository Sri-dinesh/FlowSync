from dataclasses import FrozenInstanceError, replace
from types import SimpleNamespace

import pytest

from research.observation.arrival_tracks import Calibration, Track, Packet, TrackSensor, TrackFaults, TrackHistory
from server.app.simulation.traffic_math import MOVEMENT_KEYS


def calibration():
    return Calibration(dedicated_movement_lanes=True)


def packet(step, position=.1, source=None, movement="north_straight"):
    return Packet(step if source is None else source, step, calibration().sha256, (Track(0, movement, position),))


def test_missing_prospective_calibration_and_malformed_packets_are_rejected():
    with pytest.raises(ValueError, match="prospective"):
        Calibration(dedicated_movement_lanes=False)
    with pytest.raises(ValueError, match="future"):
        Packet(4, 3, calibration().sha256, ())
    with pytest.raises(ValueError, match="Malformed"):
        Packet(0, 0, calibration().sha256, (Track(1, "north_left", .1), Track(1, "north_left", .2)))
    with pytest.raises(ValueError, match="calibrated"):
        Track(1, "unknown_turn", .1)
    with pytest.raises(ValueError):
        Track(1, "north_left", float("nan"))
    value = packet(0).to_dict()
    value["hidden_future"] = [1, 2]
    with pytest.raises(ValueError, match="Unexpected"):
        Packet.parse(value)
    with pytest.raises(FrozenInstanceError):
        packet(0).tracks[0].position = .9


def test_motion_uses_advancing_source_positions_and_repeated_frames_are_idempotent():
    history = TrackHistory(calibration())
    first = history.observe(packet(0))
    assert first.motions[0].kind == "unknown"
    for step in range(1, 7):
        state = history.observe(packet(step, .1+.012*step))
    assert state.motions[0].kind == "moving"
    assert state.motions[0].speed[1] == pytest.approx(.12)
    count = len(history.history[0])
    repeated = history.observe(replace(state.packet, delivered_tick=9))
    assert repeated.motions == state.motions and len(history.history[0]) == count
    assert repeated.packet.age_s == pytest.approx(.3)
    assert history.observe(repeated.packet) == repeated
    with pytest.raises(ValueError, match="regressed"):
        history.observe(replace(state.packet, delivered_tick=8))
    with pytest.raises(ValueError, match="contents changed"):
        history.observe(packet(10, .3, source=6))
    assert history.observe(repeated.packet) == repeated  # Rejection did not advance the clock.


def test_stopping_restarts_and_gaps_do_not_invent_free_speed():
    history = TrackHistory(calibration())
    history.observe(packet(0))
    stopped = history.observe(packet(1))
    assert stopped.motions[0].kind == "stopped" and stopped.motions[0].speed is None
    changed = history.observe(packet(2, .1, movement="north_left"))
    assert changed.motions[0].kind == "unknown"
    gap = history.observe(packet(20, .2, movement="north_left"))
    assert gap.motions[0].kind == "unknown"
    backward = history.observe(packet(21, .1, movement="north_left"))
    assert backward.motions[0].kind == "unknown"
    impossible = history.observe(packet(26, .4, movement="north_left"))
    assert impossible.motions[0].kind == "unknown"


def test_latency_startup_and_full_drop_preserve_missingness():
    sensor = TrackSensor(calibration(), TrackFaults(latency_ticks=2), 5)
    for step in range(2):
        state = sensor.replay((Track(0, "north_left", .1+.01*step),), step)
        assert state.packet.source_tick is None and not state.motions
    state = sensor.replay((Track(0, "north_left", .12),), 2)
    assert state.packet.source_tick == 0 and state.packet.tracks[0].position == .1
    assert state.packet.age_s == pytest.approx(.2)
    full_drop = TrackSensor(calibration(), TrackFaults(frame_drop_probability=1.), 5)
    for step in range(10):
        assert full_drop.replay((Track(0, "north_left", .1),), step).packet.source_tick is None


def test_missed_tracks_cannot_reappear_as_clean_counts_and_replay_is_exact():
    faults = TrackFaults(miss_rate=.2, latency_ticks=2, frame_drop_probability=.3, position_error=.002)
    first, second = TrackSensor(calibration(), faults, 10), TrackSensor(calibration(), faults, 10)
    old_sources = []
    for step in range(20):
        raw = tuple(Track(i, MOVEMENT_KEYS[i], .1+.005*step) for i in range(12))
        state, replay = first.replay(raw, step), second.replay(raw, step)
        assert state == replay
        assert sum(state.counts("all").values()) == len(state.packet.tracks)
        old_sources.append(state.packet.source_tick)
    assert any(a == b and a is not None for a, b in zip(old_sources, old_sources[1:]))
    missed = TrackSensor(calibration(), TrackFaults(miss_rate=1.), 10).replay(raw, 0)
    assert not missed.packet.tracks and not any(missed.counts().values())
    with pytest.raises(ValueError, match="advance"):
        first.replay(raw, 19)
    with pytest.raises(ValueError, match="bound"):
        TrackSensor(calibration(), TrackFaults(position_error=.003), 1)


def test_capture_reads_only_declared_geometry_position_and_remapped_identity():
    def intersection(identifier):
        lanes = {m: [] for m in MOVEMENT_KEYS}
        lanes["north_left"] = [SimpleNamespace(id=identifier, position=.2)]
        return SimpleNamespace(lanes=lanes)
    first = TrackSensor(calibration(), TrackFaults(), 10).observe(intersection("random-uuid-A"), 0)
    second = TrackSensor(calibration(), TrackFaults(), 10).observe(intersection("random-uuid-B"), 0)
    assert first == second and first.packet.tracks == (Track(0, "north_left", .2),)


def test_counts_exclude_unseen_backlog_and_separate_upstream_from_discharged():
    sensor = TrackSensor(calibration(), TrackFaults(), 10)
    raw = (Track(0, "north_straight", .1), Track(1, "north_left", .95))
    state = sensor.replay(raw, 0)
    assert sum(state.counts("all").values()) == 2
    assert sum(state.counts().values()) == 1
    assert sum(state.counts("queued").values()) == 1  # Unknown motion is conservative queued demand.
    assert state.outgoing()["east"] == 1
    assert state.outgoing(queued=True)["east"] == 1
