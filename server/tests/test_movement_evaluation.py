import copy
import json

import pytest
from pydantic import ValidationError

from research.cv.evaluate_crossings import Protocol, Session, digest
from research.cv.evaluate_movements import (
    MovementAnnotations, MovementPredictions, evaluate, run, verify,
)
from server.tests.test_crossing_evaluation import fixture as crossing_fixture


def fixture():
    session, annotations, protocol, video_hash = crossing_fixture()
    annotations["schema_version"] = "movement_annotations_v1"
    annotations["events"][0]["turn"] = "left"
    annotations["events"][1]["turn"] = "right"
    predictions = dict(schema_version="movement_predictions_v1", session_sha256=digest(json.dumps(session).encode()),
                       video_sha256=video_hash, calibration_sha256=session["calibration_sha256"],
                       origin="synthetic_fixture", producer_id="fixture",
                       producer_method="Analytic synthetic predictions for scorer verification only.",
                       events=[dict(prediction_index=0, turn="left", available_time_s=1.)])
    return session, annotations, protocol, video_hash, predictions


def score(session, annotations, protocol, video_hash, predictions=None):
    return evaluate(Session.model_validate(session), MovementAnnotations.model_validate(annotations),
                    Protocol.model_validate(protocol), video_hash, digest(json.dumps(session).encode()),
                    MovementPredictions.model_validate(predictions) if predictions is not None else None)


def test_current_pipeline_abstains_instead_of_becoming_straight():
    s, a, p, h, _ = fixture()
    report = score(s, a, p, h)
    m = report["metrics"]
    assert m["known_turn_labels"] == 2
    assert m["abstained_known_matches"] == m["missed_known_turn_labels"] == 1
    assert m["accuracy_among_classified_known_matches"] is None
    assert m["classification_coverage_among_known_matches"] == 0
    assert m["correct_turn_fraction_of_all_known_labels"] == 0
    assert m["confusion"]["left"]["abstain"] == m["confusion"]["right"]["missed_crossing"] == 1
    assert report["matches"][0]["available_time_s"] == 1
    assert not report["publication_ready"] and not report["physical_actuation"]


def test_perfect_conditional_accuracy_does_not_hide_missed_turns():
    report = score(*fixture())
    assert report["metrics"]["accuracy_among_classified_known_matches"] == 1
    assert report["metrics"]["correct_turn_fraction_of_all_known_labels"] == .5
    assert report["metrics"]["mean_availability_delay_after_estimated_crossing_s"] == .5
    assert not report["availability_times_verified"]
    assert report["per_approach"]["north"] == report["metrics"]


@pytest.mark.parametrize("turn", ["straight", "right", "u_turn"])
def test_wrong_turn_is_not_a_correct_event_just_because_approach_matches(turn):
    s, a, p, h, predictions = fixture()
    predictions["events"][0]["turn"] = turn
    report = score(s, a, p, h, predictions)
    assert report["crossing_evaluation"]["metrics"]["true_positive"] == 1
    assert report["metrics"]["wrong_known_matches"] == 1
    assert report["metrics"]["accuracy_among_classified_known_matches"] == 0
    assert report["metrics"]["confusion"]["left"][turn] == 1


def test_turns_do_not_influence_matching_and_cannot_be_rematched_for_a_better_score():
    s, a, p, h, predictions = fixture()
    second = copy.deepcopy(s["stop_line_crossings"][0])
    second.update(track_id=2, estimated_time_s=.7)
    s["stop_line_crossings"].append(second)
    s["frames"][1]["crossing_observation"]["events"].append(second)
    for frame in (s["frames"][1:]):
        frame["crossing_observation"]["counts"]["north"] = 2
    a["events"][0].update(time_s=.5, turn="right")
    a["events"][1].update(time_s=.7, turn="left")
    p["match_tolerance_s"] = .3
    predictions["events"].append(dict(prediction_index=1, turn="right", available_time_s=1.))
    predictions["session_sha256"] = digest(json.dumps(s).encode())
    report = score(s, a, p, h, predictions)
    assert report["metrics"]["wrong_known_matches"] == 2
    assert report["metrics"]["correct_known_matches"] == 0
    assert [row["prediction_index"] for row in report["matches"]] == [0, 1]


def test_unknown_ground_truth_is_retained_but_excluded_from_accuracy():
    s, a, p, h, predictions = fixture()
    for label in a["events"]:
        label.update(turn=None, unknown_reason="Exit is outside the recorded field of view.")
    report = score(s, a, p, h, predictions)
    assert report["metrics"]["unknown_turn_labels"] == 2
    assert report["metrics"]["confusion"]["unknown"]["left"] == 1
    assert report["metrics"]["confusion"]["unknown"]["missed_crossing"] == 1
    assert report["metrics"]["correct_turn_fraction_of_all_known_labels"] is None
    assert report["metrics"]["accuracy_among_classified_known_matches"] is None


def test_unmatched_predictions_and_unscored_time_are_not_hidden():
    s, a, p, h, predictions = fixture()
    a["events"] = a["events"][1:]
    report = score(s, a, p, h, predictions)
    assert report["unmatched_prediction_turn_counts"]["left"] == 1
    assert report["unmatched_predictions"][0]["prediction_index"] == 0
    assert report["metrics"]["missed_known_turn_labels"] == 1
    a["windows"][0]["start_s"] = 1
    report = score(s, a, p, h, predictions)
    assert report["unmatched_predictions"] == []
    assert report["crossing_evaluation"]["unscored_prediction_indices"] == [0]


def test_complete_detector_outage_remains_in_end_to_end_denominator():
    s, a, p, h, _ = fixture()
    s["stop_line_crossings"] = []
    for frame in s["frames"]:
        frame["crossing_observation"].update(status="geometry_unavailable", counts={"north": 0}, events=[])
    report = score(s, a, p, h)
    assert report["metrics"]["missed_known_turn_labels"] == 2
    assert report["metrics"]["correct_turn_fraction_of_all_known_labels"] == 0
    assert report["metrics"]["classification_coverage_among_known_matches"] is None


@pytest.mark.parametrize("fault", ["session", "video", "calibration", "missing", "duplicate", "extra",
                                  "early", "past_end", "nonfinite", "coerced_index", "human_prediction"])
def test_invalid_prediction_evidence_is_rejected(fault):
    s, a, p, h, predictions = fixture()
    if fault in ("session", "video", "calibration"):
        predictions[f"{fault}_sha256"] = "a"*64
    elif fault == "missing": predictions["events"] = []
    elif fault == "duplicate": predictions["events"] *= 2
    elif fault == "extra": predictions["events"].append(dict(prediction_index=1, turn=None, available_time_s=2.))
    elif fault == "early": predictions["events"][0]["available_time_s"] = .75
    elif fault == "past_end": predictions["events"][0]["available_time_s"] = 4.
    elif fault == "nonfinite": predictions["events"][0]["available_time_s"] = float("nan")
    elif fault == "coerced_index": predictions["events"][0]["prediction_index"] = True
    else: predictions["origin"] = "human"
    with pytest.raises((ValueError, ValidationError)):
        score(s, a, p, h, predictions)


@pytest.mark.parametrize("patch", [{"turn": None}, {"turn": None, "unknown_reason": " "},
                                  {"turn": "left", "unknown_reason": "occluded"}, {"turn": "north"}])
def test_unknown_truth_requires_an_explanation_and_known_truth_a_supported_turn(patch):
    s, a, p, h, _ = fixture()
    a["events"][0].update(patch)
    with pytest.raises(ValidationError): score(s, a, p, h)


def test_annotations_must_explicitly_supply_turn_even_when_unknown():
    s, a, p, h, _ = fixture()
    del a["events"][0]["turn"]
    with pytest.raises(ValidationError): score(s, a, p, h)


@pytest.mark.parametrize("with_predictions", [False, True])
def test_archived_report_reconstructs_and_rejects_overwrite_or_tampering(tmp_path, with_predictions):
    s, a, p, _, predictions = fixture()
    for name, data in [("session", s), ("annotations", a), ("protocol", p), ("predictions", predictions)]:
        (tmp_path/f"{name}.json").write_text(json.dumps(data))
    video = tmp_path/"fixture.avi"
    video.write_bytes(b"synthetic fixture bytes; not a decoded video")
    output = tmp_path/"report"
    args = [tmp_path/"session.json", tmp_path/"annotations.json", tmp_path/"protocol.json", video, output,
            tmp_path/"predictions.json" if with_predictions else None]
    report = run(*args)
    assert verify(output, video)["verified"]
    with pytest.raises(FileExistsError): run(*args)
    report["metrics"]["correct_turn_fraction_of_all_known_labels"] = 1
    (output/"report.json").write_text(json.dumps(report))
    with pytest.raises(ValueError, match="reconstruct"): verify(output, video)
