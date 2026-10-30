"""Versioned synthetic track boundary and causal position-history estimation.

Dedicated movement lanes and normalized road coordinates are research sensor
assumptions. The existing CCTV pipeline cannot currently populate this contract.
"""
from collections import deque
from dataclasses import asdict, dataclass
from functools import cached_property
import hashlib
import json
import math

import numpy as np

from server.app.simulation.traffic_math import DEST_MAP, MOVEMENT_KEYS

VERSION = "source_timed_tracks_v1"
DT = .1


@dataclass(frozen=True)
class Calibration:
    dedicated_movement_lanes: bool
    stop_line: float = .42
    max_speed: float = .12
    spacing: float = .08
    position_error: float = .002
    history_seconds: float = 1.
    minimum_span: float = .4

    def __post_init__(self):
        if self.dedicated_movement_lanes is not True:
            raise ValueError("Four-phase control requires explicitly calibrated prospective movement lanes")
        values = (self.stop_line, self.max_speed, self.spacing, self.position_error,
                  self.history_seconds, self.minimum_span)
        if (not all(math.isfinite(v) for v in values) or not 0 < self.stop_line < 1
                or min(self.max_speed, self.spacing, self.minimum_span) <= 0
                or self.position_error < 0 or self.history_seconds < self.minimum_span):
            raise ValueError("Invalid normalized-path track calibration")

    @cached_property
    def sha256(self):
        value = dict(version=VERSION, units="normalized_path_units", **asdict(self))
        return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class Track:
    track_id: int
    movement: str
    position: float

    def __post_init__(self):
        if (type(self.track_id) is not int or self.track_id < 0 or self.movement not in MOVEMENT_KEYS
                or not math.isfinite(self.position) or not 0 <= self.position <= 1):
            raise ValueError("Track requires a session ID, calibrated movement and normalized position")


@dataclass(frozen=True)
class Packet:
    source_tick: int | None
    delivered_tick: int
    calibration_sha256: str
    tracks: tuple[Track, ...]

    def __post_init__(self):
        if (type(self.delivered_tick) is not int or self.delivered_tick < 0
                or not isinstance(self.tracks, tuple) or not all(isinstance(t, Track) for t in self.tracks)
                or len({t.track_id for t in self.tracks}) != len(self.tracks)):
            raise ValueError("Malformed delivered track packet")
        if self.source_tick is None:
            if self.tracks:
                raise ValueError("Missing source frame cannot contain observations")
        elif type(self.source_tick) is not int or not 0 <= self.source_tick <= self.delivered_tick:
            raise ValueError("Source timestamp must not be future or negative")

    @property
    def age_s(self):
        return None if self.source_tick is None else (self.delivered_tick-self.source_tick)*DT

    def to_dict(self):
        return asdict(self)

    @classmethod
    def parse(cls, value):
        if set(value) != {"source_tick", "delivered_tick", "calibration_sha256", "tracks"}:
            raise ValueError("Unexpected delivered-packet fields")
        return cls(value["source_tick"], value["delivered_tick"], value["calibration_sha256"],
                   tuple(Track(**t) for t in value["tracks"]))


@dataclass(frozen=True)
class Motion:
    track: Track
    kind: str  # moving, stopped, unknown
    speed: tuple[float, float, float] | None = None  # lower, nominal, upper

    def __post_init__(self):
        if self.kind not in ("moving", "stopped", "unknown"):
            raise ValueError("Unknown motion state")
        if self.kind == "moving":
            if (not isinstance(self.speed, tuple) or len(self.speed) != 3
                    or not all(math.isfinite(v) for v in self.speed)
                    or not 0 < self.speed[0] <= self.speed[1] <= self.speed[2]):
                raise ValueError("Moving track requires a positive finite ordered speed interval")
        elif self.speed is not None:
            raise ValueError("Stopped/unknown tracks cannot carry invented motion estimates")


@dataclass(frozen=True)
class DeliveredState:
    packet: Packet
    motions: tuple[Motion, ...]
    calibration: Calibration

    def counts(self, subset="upstream"):
        if subset not in ("all", "upstream", "queued"):
            raise ValueError("Unknown track-count subset")
        result = dict.fromkeys(MOVEMENT_KEYS, 0)
        for motion in self.motions:
            if subset != "all" and motion.track.position > self.calibration.stop_line:
                continue
            if subset == "queued" and motion.kind == "moving":
                continue
            result[motion.track.movement] += 1
        return result

    def outgoing(self, *, queued=False):
        result = dict.fromkeys(("north", "south", "east", "west"), 0)
        for motion in self.motions:
            observed = motion.track.position > (self.calibration.stop_line if queued else .9)
            if observed and (not queued or motion.kind != "moving"):
                result[DEST_MAP[motion.track.movement]] += 1
        return result


class TrackHistory:
    def __init__(self, calibration):
        self.calibration = calibration
        self.history = {}
        self.last_source = None
        self.last_tracks = ()
        self.motions = ()
        self.last_delivered = None

    def observe(self, packet):
        if packet.calibration_sha256 != self.calibration.sha256:
            raise ValueError("Track geometry/calibration mismatch")
        if self.last_delivered is not None:
            if (packet.delivered_tick < self.last_delivered.delivered_tick or
                    (packet.delivered_tick == self.last_delivered.delivered_tick and packet != self.last_delivered)):
                raise ValueError("Control delivery time regressed or changed at the same tick")
        source = packet.source_tick
        if source is None:
            if self.last_source is not None:
                raise ValueError("Delivered source time disappeared")
            self.last_delivered = packet
            return DeliveredState(packet, (), self.calibration)
        if self.last_source is not None and source <= self.last_source:
            if source != self.last_source or packet.tracks != self.last_tracks:
                raise ValueError("Source time regressed or repeated frame contents changed")
            self.last_delivered = packet
            return DeliveredState(packet, self.motions, self.calibration)
        motions = []
        error = self.calibration.position_error
        for track in packet.tracks:
            history = self.history.setdefault(track.track_id, deque())
            if history and (history[-1][2] != track.movement or
                            (source-history[-1][0])*DT > self.calibration.history_seconds):
                history.clear()
            while history and (source-history[0][0])*DT > self.calibration.history_seconds+1e-9:
                history.popleft()
            kind, speed = "unknown", None
            if history:
                adjacent = track.position-history[-1][1]
                if abs(adjacent) <= 2*error+1e-9:
                    kind = "stopped"
                elif adjacent < -2*error:
                    history.clear()
                elif (source-history[0][0])*DT >= self.calibration.minimum_span-1e-9:
                    elapsed = (source-history[0][0])*DT
                    displacement = track.position-history[0][1]
                    lower = max(0., (displacement-2*error)/elapsed)
                    upper = min(self.calibration.max_speed, (displacement+2*error)/elapsed)
                    if upper > 0 and 0 < lower <= upper+1e-9:
                        lower = min(lower, upper)
                        nominal = min(upper, max(lower, displacement/elapsed))
                        kind, speed = "moving", (lower, nominal, upper)
                    elif lower > upper+1e-9:
                        history.clear()
            history.append((source, track.position, track.movement))
            motions.append(Motion(track, kind, speed))
        self.history = {key: rows for key, rows in self.history.items()
                        if rows and (source-rows[-1][0])*DT <= self.calibration.history_seconds}
        self.last_source, self.last_tracks, self.motions = source, packet.tracks, tuple(motions)
        self.last_delivered = packet
        return DeliveredState(packet, self.motions, self.calibration)


@dataclass(frozen=True)
class TrackFaults:
    name: str = "clean_tracks"
    miss_rate: float = 0.
    latency_ticks: int = 0
    frame_drop_probability: float = 0.
    position_error: float = 0.

    def __post_init__(self):
        if (not all(math.isfinite(v) for v in (self.miss_rate, self.frame_drop_probability, self.position_error))
                or not 0 <= self.miss_rate <= 1 or not 0 <= self.frame_drop_probability <= 1
                or self.position_error < 0 or type(self.latency_ticks) is not int or self.latency_ticks < 0):
            raise ValueError("Invalid synthetic track faults")


class TrackSensor:
    """Sole simulator-object reader; offline replay uses the same delivery owner."""
    def __init__(self, calibration, faults, seed):
        if faults.position_error > calibration.position_error:
            raise ValueError("Synthetic position errors exceed the declared engineering bound")
        self.calibration, self.faults, self.seed = calibration, faults, int(seed)
        self.ids, self.last_snapshot = {}, ()
        self.buffer = deque(maxlen=faults.latency_ticks+1)
        self.last_packet = None
        self.last_step = -1
        self.history = TrackHistory(calibration)

    def observe(self, intersection, step):
        samples = []
        for movement in MOVEMENT_KEYS:
            for vehicle in intersection.lanes[movement]:
                if 0 <= vehicle.position < 1:
                    if vehicle.id not in self.ids:
                        self.ids[vehicle.id] = len(self.ids)
                    # Prospective label is an explicit lane-geometry assumption;
                    # no vehicle.turn/speed/state/wait/future is read here.
                    samples.append(Track(self.ids[vehicle.id], movement, float(vehicle.position)))
        return self.replay(tuple(samples), step)

    def replay(self, snapshot, step):
        if type(step) is not int or step <= self.last_step:
            raise ValueError("Track capture ticks must advance")
        if not isinstance(snapshot, tuple) or not all(isinstance(t, Track) for t in snapshot):
            raise ValueError("Synthetic capture must contain immutable measurements")
        self.last_step, self.last_snapshot = step, snapshot
        schedule = np.random.default_rng(np.random.SeedSequence([self.seed, step, 41]))
        dropped = schedule.random() < self.faults.frame_drop_probability
        received = []
        for sample in snapshot:
            rng = np.random.default_rng(np.random.SeedSequence([self.seed, step, sample.track_id, 42]))
            if rng.random() < self.faults.miss_rate:
                continue
            position = float(np.clip(sample.position+rng.uniform(-self.faults.position_error, self.faults.position_error), 0, 1))
            received.append(Track(sample.track_id, sample.movement, position))
        self.buffer.append((step, tuple(received)))
        if not dropped and len(self.buffer) == self.buffer.maxlen:
            self.last_packet = self.buffer[0]
        source, tracks = self.last_packet if self.last_packet else (None, ())
        packet = Packet(source, step, self.calibration.sha256, tracks)
        return self.history.observe(packet)
