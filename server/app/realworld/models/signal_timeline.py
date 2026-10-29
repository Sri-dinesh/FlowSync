"""Read-only signal annotations on the recorded video's timestamp axis."""
import bisect
import hashlib
import json
import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Time = Annotated[float, Field(ge=0, allow_inf_nan=False, strict=True)]
Phase = Annotated[int, Field(ge=0, le=3, strict=True)]
Color = Literal["green", "yellow", "all_red", "unknown"]


class SignalSegment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    start_s: Time
    end_s: Time
    state: Color
    phase: Phase | None = None
    onset_observed: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def valid_interval(self):
        if self.end_s <= self.start_s:
            raise ValueError("Signal intervals must have positive duration.")
        if (self.state in ("green", "yellow")) != (self.phase is not None):
            raise ValueError("Green/yellow require a phase; all-red/unknown must not name one.")
        if self.state == "unknown" and self.onset_observed:
            raise ValueError("Unknown signal state cannot have an observed state onset.")
        return self


class RecordedSignal(BaseModel):
    status: Literal["available", "unknown", "gap", "source_timing_unavailable", "video_mismatch"]
    timeline_sha256: str
    origin: str
    source_time_s: float | None = None
    state: Color | None = None
    phase: int | None = None
    state_elapsed_s: float | None = None
    green_elapsed_s: float | None = None
    onset_observed: bool = False
    time_resolution_s: float


class SignalTimeline(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal["recorded_signal_v1"] = "recorded_signal_v1"
    video_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    timebase: Literal["video_position_seconds"] = "video_position_seconds"
    phase_mapping: Literal["flowsync_four_phase_v1"] = "flowsync_four_phase_v1"
    origin: Literal["human_annotation", "synchronized_controller_log", "synthetic_fixture"]
    annotation_method: Annotated[str, Field(min_length=10, max_length=4000)]
    time_resolution_s: Annotated[float, Field(gt=0, allow_inf_nan=False, strict=True)]
    segments: Annotated[tuple[SignalSegment, ...], Field(min_length=1, max_length=10000)]

    @model_validator(mode="after")
    def ordered_segments(self):
        for previous, current in zip(self.segments, self.segments[1:]):
            if current.start_s < previous.end_s:
                raise ValueError("Signal intervals must be ordered and must not overlap.")
            if current.start_s == previous.end_s and (current.state, current.phase) == (previous.state, previous.phase):
                raise ValueError("Merge adjacent intervals of the same state/phase; do not reset their onset.")
        return self

    def canonical_json(self):
        return json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), allow_nan=False)

    @property
    def sha256(self):
        return hashlib.sha256(self.canonical_json().encode()).hexdigest()


class SignalTimelineReader:
    def __init__(self, timeline: SignalTimeline):
        self.timeline = timeline
        self._starts = tuple(segment.start_s for segment in timeline.segments)
        self._sha256 = timeline.sha256

    def at(self, source_time_s, video_sha256):
        valid_time = source_time_s is not None and math.isfinite(source_time_s) and source_time_s >= 0
        result = RecordedSignal(status="gap", timeline_sha256=self._sha256,
                                origin=self.timeline.origin, time_resolution_s=self.timeline.time_resolution_s,
                                source_time_s=source_time_s if valid_time else None)
        if video_sha256 != self.timeline.video_sha256:
            result.status = "video_mismatch"
            return result
        if not valid_time:
            result.status = "source_timing_unavailable"
            return result
        index = bisect.bisect_right(self._starts, source_time_s)-1
        if index < 0 or source_time_s >= self.timeline.segments[index].end_s:
            return result
        segment = self.timeline.segments[index]
        result.status = "unknown" if segment.state == "unknown" else "available"
        result.state, result.phase = segment.state, segment.phase
        result.onset_observed = segment.onset_observed
        if segment.onset_observed:
            result.state_elapsed_s = source_time_s-segment.start_s
            if segment.state == "green":
                result.green_elapsed_s = result.state_elapsed_s
        return result
