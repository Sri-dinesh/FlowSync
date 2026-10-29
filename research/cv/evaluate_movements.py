"""Offline turn-label evaluation with explicit abstentions and observation times."""
import argparse
import json
from pathlib import Path
import statistics
import sys
from typing import Annotated, Literal

import pydantic
from pydantic import Field, model_validator

from research.cv.evaluate_crossings import (
    Annotations, Hash, Identifier, Label, Protocol, ROOT, Session, StrictModel, Time,
    digest, evaluate as evaluate_crossings, video_digest,
)

Turn = Literal["straight", "left", "right", "u_turn"]
TURNS = ("straight", "left", "right", "u_turn")


class MovementLabel(Label):
    turn: Turn | None
    unknown_reason: Annotated[str, Field(min_length=1, max_length=1000)] | None = None

    @model_validator(mode="after")
    def explain_unknown(self):
        if (self.turn is None) != (self.unknown_reason is not None):
            raise ValueError("Unknown turns require a reason; known turns must not have one.")
        if self.unknown_reason is not None and not self.unknown_reason.strip():
            raise ValueError("Unknown-turn reasons must not be blank.")
        return self


class MovementAnnotations(Annotations):
    schema_version: Literal["movement_annotations_v1"]
    events: list[MovementLabel]


class MovementPrediction(StrictModel):
    prediction_index: Annotated[int, Field(ge=0, strict=True)]
    turn: Turn | None
    available_time_s: Time


class MovementPredictions(StrictModel):
    schema_version: Literal["movement_predictions_v1"]
    session_sha256: Hash
    video_sha256: Hash
    calibration_sha256: Hash
    origin: Literal["model", "synthetic_fixture"]
    producer_id: Identifier
    producer_method: Annotated[str, Field(min_length=10, max_length=4000)]
    events: list[MovementPrediction]

    @model_validator(mode="after")
    def unique_indices(self):
        if len({event.prediction_index for event in self.events}) != len(self.events):
            raise ValueError("Prediction indices must be unique.")
        return self


def prediction_rows(session, predictions, session_sha256, coverage):
    if predictions is None:
        # Explicit abstaining baseline. Retrospective exit outcomes require the
        # separate trajectory export; *_straight count slots are not turns.
        return {i: MovementPrediction(prediction_index=i, turn=None, available_time_s=event.time_interval_s[1])
                for i, event in enumerate(session.stop_line_crossings)}
    if (predictions.session_sha256 != session_sha256
        or predictions.video_sha256 != session.source_video_sha256
        or predictions.calibration_sha256 != session.calibration_sha256):
        raise ValueError("Movement predictions target different session, video or calibration bytes.")
    rows = {row.prediction_index: row for row in predictions.events}
    if set(rows) != set(range(len(session.stop_line_crossings))):
        raise ValueError("Supply exactly one prediction, including explicit abstentions, for every recorded crossing.")
    for i, event in enumerate(session.stop_line_crossings):
        if not event.time_interval_s[1] <= rows[i].available_time_s <= coverage["last_source_time_s"]:
            raise ValueError("Prediction availability must be at/after the crossing's bracketing frame and within recorded time.")
    return rows


def summarize(labels, matches, predictions):
    """Count every labeled event; unknown truth never becomes an accuracy target."""
    confusion = {truth: {prediction: 0 for prediction in (*TURNS, "abstain", "missed_crossing")}
                 for truth in (*TURNS, "unknown")}
    known = matched_known = classified = correct = 0
    delays = []
    for label in labels:
        match = matches.get(label.event_id)
        prediction = predictions[match["prediction_index"]] if match else None
        column = "missed_crossing" if prediction is None else prediction.turn or "abstain"
        confusion[label.turn or "unknown"][column] += 1
        if label.turn is None:
            continue
        known += 1
        if prediction is None:
            continue
        matched_known += 1
        if prediction.turn is not None:
            classified += 1
            correct += prediction.turn == label.turn
            delays.append(match["availability_delay_after_estimated_crossing_s"])
    return dict(
        labeled_crossings=len(labels), known_turn_labels=known, unknown_turn_labels=len(labels)-known,
        matched_known_turn_labels=matched_known, missed_known_turn_labels=known-matched_known,
        classified_known_matches=classified, abstained_known_matches=matched_known-classified,
        correct_known_matches=correct, wrong_known_matches=classified-correct,
        classification_coverage_among_known_matches=classified/matched_known if matched_known else None,
        accuracy_among_classified_known_matches=correct/classified if classified else None,
        correct_turn_fraction_of_all_known_labels=correct/known if known else None,
        mean_availability_delay_after_estimated_crossing_s=statistics.mean(delays) if delays else None,
        max_availability_delay_after_estimated_crossing_s=max(delays) if delays else None,
        confusion=confusion,
    )


def evaluate(session, annotations, protocol, video_hash, session_hash, predictions=None):
    crossing_report = evaluate_crossings(session, annotations, protocol, video_hash)
    rows = prediction_rows(session, predictions, session_hash, crossing_report["coverage"])
    labels = {label.event_id: label for label in annotations.events}
    matched = []
    for match in crossing_report["matches"]:
        row = rows[match["prediction_index"]]
        event = session.stop_line_crossings[match["prediction_index"]]
        label = labels[match["annotation_id"]]
        matched.append(dict(**match, annotated_turn=label.turn, unknown_reason=label.unknown_reason,
                            predicted_turn=row.turn, available_time_s=row.available_time_s,
                            availability_delay_after_estimated_crossing_s=row.available_time_s-event.estimated_time_s))
    by_label = {match["annotation_id"]: match for match in matched}
    unmatched = [dict(prediction_index=i, turn=rows[i].turn, available_time_s=rows[i].available_time_s)
                 for i in crossing_report["unmatched_prediction_indices"]]
    return dict(
        schema_version="movement_evaluation_v1", complete=True,
        prediction_source=predictions.model_dump(exclude={"events"}) if predictions else {
            "origin": "recorded_pipeline", "producer_id": "unavailable_turn_classifier",
            "producer_method": "Crossing-only abstaining baseline; retrospective exit outcomes are not imported without a predictions file."},
        crossing_evaluation=crossing_report,
        metrics=summarize(annotations.events, by_label, rows),
        per_approach={approach: summarize([label for label in annotations.events if label.approach == approach], by_label, rows)
                      for approach in sorted({window.approach for window in annotations.windows})},
        matches=matched, unmatched_predictions=unmatched,
        unmatched_prediction_turn_counts={turn: sum(row["turn"] == turn for row in unmatched) for turn in TURNS},
        unmatched_prediction_abstentions=sum(row["turn"] is None for row in unmatched),
        publication_ready=False, policy_promoted=False, physical_actuation=False,
        availability_times_verified=False,
        scope="Offline turn agreement after approach/time matching, not vehicle identity, causal queue inputs or control performance. Availability times are producer declarations, not independently verified latency.",
    )


def build_report(inputs, video_hash):
    report = evaluate(
        Session.model_validate_json(inputs["session.json"]),
        MovementAnnotations.model_validate_json(inputs["annotations.json"]),
        Protocol.model_validate_json(inputs["protocol.json"]), video_hash, digest(inputs["session.json"]),
        MovementPredictions.model_validate_json(inputs["predictions.json"]) if "predictions.json" in inputs else None,
    )
    sources = {name: (ROOT/name).read_bytes() for name in (
        "research/cv/evaluate_movements.py", "research/cv/evaluate_crossings.py",
        "server/app/realworld/models/calibration.py", "server/app/realworld/models/crossings.py")}
    report.update(input_sha256={name: digest(data) for name, data in inputs.items()}, video_sha256=video_hash,
                  source_sha256={name: digest(data) for name, data in sources.items()},
                  python_version=sys.version, pydantic_version=pydantic.__version__)
    return report, sources


def run(session_path, annotations_path, protocol_path, video_path, output, predictions_path=None):
    inputs = {name: path.read_bytes() for name, path in (
        ("session.json", session_path), ("annotations.json", annotations_path), ("protocol.json", protocol_path))}
    if predictions_path is not None:
        inputs["predictions.json"] = predictions_path.read_bytes()
    report, sources = build_report(inputs, video_digest(video_path))
    output.mkdir(parents=True, exist_ok=False)
    for name, data in inputs.items():
        (output/name).write_bytes(data)
    for name, data in sources.items():
        target = output/"source"/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (output/"report.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    return report


def verify(output, video_path):
    inputs = {name: (output/name).read_bytes() for name in ("session.json", "annotations.json", "protocol.json")}
    if (output/"predictions.json").exists():
        inputs["predictions.json"] = (output/"predictions.json").read_bytes()
    rebuilt, sources = build_report(inputs, video_digest(video_path))
    if (json.loads((output/"report.json").read_text()) != rebuilt
        or any((output/"source"/name).read_bytes() != data for name, data in sources.items())):
        raise ValueError("Report, inputs or source do not reconstruct; historical reports require their archived implementation/runtime.")
    return dict(verified=True, scope="Stored events, input/source hashes and movement scoring reconstructed; no detector or trajectory rerun.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("session", "annotations", "protocol", "predictions", "output", "verify"):
        parser.add_argument(f"--{name}", type=Path)
    parser.add_argument("--video", type=Path, required=True)
    args = parser.parse_args()
    if args.verify:
        if any((args.session, args.annotations, args.protocol, args.predictions, args.output)):
            parser.error("--verify accepts only --video alongside it.")
        print(json.dumps(verify(args.verify, args.video), indent=2))
        return
    if not all((args.session, args.annotations, args.protocol, args.output)):
        parser.error("Evaluation requires --session, --annotations, --protocol and --output.")
    report = run(args.session, args.annotations, args.protocol, args.video, args.output, args.predictions)
    print(json.dumps({"complete": True, "metrics": report["metrics"], "publication_ready": False}, indent=2))


if __name__ == "__main__":
    main()
