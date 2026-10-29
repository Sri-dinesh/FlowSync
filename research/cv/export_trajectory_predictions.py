"""Export recorded retrospective turn outcomes for the movement evaluator."""
import argparse
import json
from pathlib import Path

from pydantic import BaseModel

from research.cv.evaluate_crossings import Session, check_session, digest
from research.cv.evaluate_movements import MovementPredictions
from server.app.realworld.models.trajectory_turns import TrajectoryObservation, TrajectoryTurn


class TurnFrame(BaseModel):
    frame_id: int
    trajectory_observation: TrajectoryObservation | None = None


class TurnSession(BaseModel):
    trajectory_turns: list[TrajectoryTurn]
    frames: list[TurnFrame]  # Full crossing frames are validated separately by Session.


def export(session_bytes):
    session = Session.model_validate_json(session_bytes)
    coverage = check_session(session)
    turns = TurnSession.model_validate_json(session_bytes)
    if not session.calibration.exits:
        raise ValueError("Session has no configured exit regions.")
    # Keep the exact frame-level and aggregate evidence linked before converting.
    flattened = [event for frame in turns.frames if frame.trajectory_observation
                 for event in frame.trajectory_observation.events]
    if flattened != turns.trajectory_turns:
        raise ValueError("Aggregate turn outcomes differ from recorded frame events.")
    keys = {(event.track_id, event.approach, event.frame_id): i for i, event in enumerate(session.stop_line_crossings)}
    source_times = {frame.frame_id: frame.crossing_observation for frame in session.frames if frame.crossing_observation}
    outcomes = {}
    for frame in turns.frames:
        observation = frame.trajectory_observation
        if observation is None:
            continue
        if observation.calibration_sha256 != session.calibration_sha256:
            raise ValueError("Trajectory observation calibration mismatch.")
        for event in observation.events:
            key = (event.track_id, event.approach, event.crossing_frame_id)
            if key not in keys or key in outcomes or event.frame_id != frame.frame_id or event.calibration_sha256 != session.calibration_sha256:
                raise ValueError("Turn outcome identity, frame or calibration mismatch.")
            crossing = session.stop_line_crossings[keys[key]]
            if event.frame_id < crossing.frame_id:
                raise ValueError("Turn outcome precedes its crossing.")
            if event.turn is not None:
                source = source_times.get(frame.frame_id)
                region = next((r for r in session.calibration.exits if r.exit_id == event.exit_id), None)
                if (observation.status != "available" or source is None or source.status != "available"
                    or source.source_time_s != event.available_time_s or frame.frame_id <= crossing.frame_id
                    or event.available_time_s < crossing.time_interval_s[1]
                    or region is None or region.turns_from.get(event.approach) != event.turn):
                    raise ValueError("Confirmed turn does not match recorded time or configured exit mapping.")
            outcomes[key] = event
    rows = []
    for event in session.stop_line_crossings:
        outcome = outcomes.get((event.track_id, event.approach, event.frame_id))
        known = outcome is not None and outcome.turn is not None
        rows.append(dict(prediction_index=len(rows), turn=outcome.turn if known else None,
                         available_time_s=outcome.available_time_s if known else coverage["last_source_time_s"]))
    return MovementPredictions(
        schema_version="movement_predictions_v1", session_sha256=digest(session_bytes),
        video_sha256=session.source_video_sha256, calibration_sha256=session.calibration_sha256,
        origin="model", producer_id="continuous_crossing_exit_v1",
        producer_method="Retrospective continuous centroid track from stop-line crossing into a mapped exit for two frames. Unresolved/unfinished tracks abstain at the recorded endpoint; availability is not independently attested.",
        events=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    predictions = export(args.session.read_bytes())
    with args.output.open("x") as output:
        output.write(json.dumps(predictions.model_dump(mode="json"), indent=2, allow_nan=False)+"\n")
    print(json.dumps(dict(complete=True, predictions=len(predictions.events), classified=sum(e.turn is not None for e in predictions.events))))


if __name__ == "__main__":
    main()
