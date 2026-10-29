"""Export recorded retrospective turn outcomes for the movement evaluator."""
import argparse
import json
from pathlib import Path

from pydantic import BaseModel

from research.cv.evaluate_crossings import Session, check_session, digest
from research.cv.evaluate_movements import MovementPredictions
from server.app.realworld.models.crossings import CrossingObservation
from server.app.realworld.models.schemas import VehicleDetection
from server.app.realworld.models.trajectory_turns import TrajectoryObservation, TrajectoryTurn
from server.app.realworld.pipeline.camera_geometry import assign_approaches
from server.app.realworld.pipeline.stop_line_crossings import StopLineCrossings
from server.app.realworld.pipeline.trajectory_turns import TrajectoryTurns


class TurnFrame(BaseModel):
    frame_id: int
    trajectory_observation: TrajectoryObservation | None = None
    trajectory_detection: VehicleDetection | None = None
    crossing_observation: CrossingObservation | None = None


class TurnSession(BaseModel):
    trajectory_turns: list[TrajectoryTurn]
    frames: list[TurnFrame]


def export(session_bytes):
    session = Session.model_validate_json(session_bytes)
    coverage = check_session(session)
    turns = TurnSession.model_validate_json(session_bytes)
    if not session.calibration.exits:
        raise ValueError("Session has no configured exit regions.")
    crossing_engine, turn_engine = StopLineCrossings(session.calibration), TrajectoryTurns(session.calibration)
    reconstructed = []
    for frame in turns.frames:
        if frame.crossing_observation is None:
            if frame.trajectory_detection is not None or frame.trajectory_observation is not None:
                raise ValueError("Trajectory evidence requires its crossing observation.")
            continue
        if frame.trajectory_detection is None or frame.trajectory_observation is None:
            raise ValueError("Recording lacks tracked detection evidence; record a new session rather than retrofit inputs.")
        detection = frame.trajectory_detection
        if detection.frame_id != frame.frame_id:
            raise ValueError("Tracked detection frame identity mismatch.")
        assignments, geometry = assign_approaches(detection, session.calibration)
        crossings = crossing_engine.update(detection, assignments, geometry, frame.crossing_observation.source_time_s)
        if crossings != frame.crossing_observation:
            raise ValueError("Crossings do not reconstruct from saved tracked boxes and source times.")
        observation = turn_engine.update(detection, crossings)
        if observation != frame.trajectory_observation:
            raise ValueError("Turn observations do not reconstruct from saved tracked boxes and source times.")
        reconstructed.extend(observation.events)
    if reconstructed != turns.trajectory_turns:
        raise ValueError("Aggregate turn outcomes differ from reconstructed frame events.")
    outcomes = {(event.track_id, event.approach, event.crossing_frame_id): event for event in reconstructed}
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
        producer_method="Crossing and two-frame exit rules re-executed from recorded tracked boxes and source times before export. Unfinished/unresolved tracks abstain at the endpoint. Detector accuracy, track identity and source timing are not independently attested.",
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
