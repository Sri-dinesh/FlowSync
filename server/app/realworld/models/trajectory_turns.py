"""Retrospective crossing-to-exit observations, separate from queued demand."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .calibration import Direction, Turn


class TrajectoryTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_semantics: Literal["retrospective_crossing_to_exit"] = "retrospective_crossing_to_exit"
    track_id: int
    crossing_frame_id: int
    approach: Direction
    calibration_sha256: str
    frame_id: int
    available_time_s: Annotated[float, Field(ge=0, allow_inf_nan=False)] | None
    exit_id: str | None = None
    turn: Turn | None = None
    reason: Literal["exit_confirmed", "track_lost", "ambiguous_exit", "unmapped_exit", "timing_gap",
                    "observation_unavailable", "implausible_displacement", "timeout"]

    @model_validator(mode="after")
    def known_only_at_exit(self):
        if (self.reason == "exit_confirmed") != (self.turn is not None):
            raise ValueError("Only confirmed exits may supply a turn.")
        if self.turn is not None and (self.exit_id is None or self.available_time_s is None):
            raise ValueError("Confirmed exits need an exit ID and availability time.")
        return self


class TrajectoryObservation(BaseModel):
    status: Literal["available", "observation_unavailable"]
    calibration_sha256: str
    max_gap_s: float = 1.
    max_displacement_px: float = 80.
    max_duration_s: float = 15.
    exit_confirmation_frames: int = 2
    pending_count: int = 0
    classified_count: int = 0
    unresolved_count: int = 0
    events: list[TrajectoryTurn] = Field(default_factory=list)
    last_event: TrajectoryTurn | None = None
