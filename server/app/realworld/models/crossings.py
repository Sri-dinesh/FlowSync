"""Inferred stop-line discharge events, distinct from demand arrivals."""
from typing import Literal
from pydantic import BaseModel, Field
from .calibration import Direction, Point


class StopLineCrossing(BaseModel):
    event_semantics: Literal["inferred_stop_line_discharge"] = "inferred_stop_line_discharge"
    track_id: int
    approach: Direction
    calibration_sha256: str
    previous_frame_id: int
    frame_id: int
    time_interval_s: tuple[float, float]
    estimated_time_s: float
    time_source: Literal["decoder_position_linear_interpolation"] = "decoder_position_linear_interpolation"
    point: Point
    turn: None = None


class CrossingObservation(BaseModel):
    status: Literal["available", "source_timing_unavailable", "geometry_unavailable"]
    source_time_s: float | None = None
    max_gap_s: float = 1.0
    deadband_px: float = 2.0
    max_displacement_px: float = 80.0
    counts: dict[Direction, int]
    events: list[StopLineCrossing] = Field(default_factory=list)
    last_event: StopLineCrossing | None = None
