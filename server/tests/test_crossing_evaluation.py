import copy
import hashlib
import itertools
import json

import pytest
from pydantic import ValidationError

from research.cv.evaluate_crossings import (Annotations, Protocol, Session, evaluate, match_events, metrics, run, verify)
from research.cv.validate_perception_quality import run_cv_validation_evaluation
from research.cv.validation_tool import CVStateValidator
from server.app.realworld.models.calibration import CameraCalibration


def fixture():
    video_hash=hashlib.sha256(b"synthetic fixture bytes; not a decoded video").hexdigest()
    config=CameraCalibration(camera_id="fixture",source="fixture.avi",frame_width=1000,frame_height=1000,
        approaches=[dict(approach="north",vertices=[[.1,.1],[.4,.1],[.4,.6],[.1,.6]],stop_line=[[.1,.6],[.4,.6]])])
    event=dict(event_semantics="inferred_stop_line_discharge",track_id=1,approach="north",calibration_sha256=config.sha256,
        previous_frame_id=1,frame_id=2,time_interval_s=[0,1],estimated_time_s=.5,
        time_source="decoder_position_linear_interpolation",point=[.25,.6],turn=None)
    session=dict(session_id="fixture",source_video_sha256=video_hash,calibration=config.model_dump(mode="json"),
        calibration_sha256=config.sha256,stop_line_crossings=[event],frames=[
            dict(frame_id=1,crossing_observation=dict(status="available",source_time_s=0,counts={"north":0})),
            dict(frame_id=2,crossing_observation=dict(status="available",source_time_s=1,counts={"north":1},events=[event])),
            dict(frame_id=3,crossing_observation=dict(status="source_timing_unavailable",counts={"north":1})),
            dict(frame_id=4,crossing_observation=dict(status="available",source_time_s=3,counts={"north":1}))])
    annotations=dict(schema_version="crossing_annotations_v1",video_sha256=video_hash,calibration_sha256=config.sha256,
        origin="synthetic_fixture",split="development",annotation_method="independently specified synthetic events",
        time_resolution_s=.1,windows=[dict(window_id="north",approach="north",start_s=0,end_s=3,exhaustive=True)],
        events=[dict(event_id="one",approach="north",time_s=.6),dict(event_id="missed",approach="north",time_s=2)])
    protocol=dict(schema_version="crossing_evaluation_v1",protocol_id="fixture",match_tolerance_s=.2)
    return session,annotations,protocol,video_hash


def score(session,annotations,protocol,video_hash):
    return evaluate(Session.model_validate(session),Annotations.model_validate(annotations),Protocol.model_validate(protocol),video_hash)


def test_one_to_one_matching_prioritizes_cardinality_over_greedy_nearest():
    pairs=match_events([(0,.19),(1,.3)],[("a",0),("b",.2)],.21)
    assert [(p,l) for p,l,_ in pairs]==[(0,"a"),(1,"b")]


def test_matching_matches_exhaustive_optimum_on_small_panels():
    for predicted in itertools.combinations([0.,.1,.3,.6],3):
        for truth in itertools.combinations([0.,.2,.4,.5],3):
            pairs=match_events(list(enumerate(predicted)),list(enumerate(truth)),.21)
            actual=(len(pairs),-sum(abs(e) for _,_,e in pairs))
            feasible=[]
            for size in range(4):
                for ps in itertools.combinations(range(3),size):
                    for ls in itertools.permutations(range(3),size):
                        errors=[abs(predicted[p]-truth[l]) for p,l in zip(ps,ls)]
                        if all(e<=.21 for e in errors): feasible.append((size,-sum(errors)))
            best=max(feasible)
            assert actual[0]==best[0] and actual[1]==pytest.approx(best[1])


def test_misses_during_unavailable_observations_are_not_dropped():
    report=score(*fixture())
    assert report["metrics"]["true_positive"]==1
    assert report["metrics"]["false_negative"]==1
    assert report["metrics"]["recall"]==.5
    assert report["metrics"]["matched_timing_mae_s"]==pytest.approx(.1)
    assert report["coverage"]["unavailable_crossing_frames"]==1
    assert report["unmatched_annotation_ids"]==["missed"]
    assert not report["publication_ready"] and not report["split_independence_verified"]


def test_empty_denominators_and_no_matches_remain_explicit():
    assert metrics(0,0,0,[])["precision"] is None
    assert metrics(0,0,0,[])["f1"] is None
    session,annotations,protocol,sha=fixture()
    annotations["events"]=[]
    result=score(session,annotations,protocol,sha)
    assert result["metrics"]["false_positive"]==1
    assert result["metrics"]["recall"] is None
    assert result["metrics"]["matched_timing_mae_s"] is None


def test_detector_outage_for_entire_clip_is_not_excluded_from_recall():
    session,annotations,protocol,sha=fixture()
    session["stop_line_crossings"]=[]
    for frame in session["frames"]:
        observation=frame["crossing_observation"]
        observation.update(status="geometry_unavailable",counts={"north":0},events=[])
    report=score(session,annotations,protocol,sha)
    assert report["metrics"]["false_negative"]==2 and report["metrics"]["recall"]==0
    assert report["coverage"]["available_crossing_frames"]==0
    assert report["coverage"]["available_timing_frames"]==3


@pytest.mark.parametrize("fault",["video", "calibration", "aggregate", "counts", "interval", "window_extent", "overlap", "nonfinite", "duplicate_label", "not_exhaustive"])
def test_invalid_evidence_is_rejected(fault):
    s,a,p,h=fixture()
    if fault=="video": h="a"*64
    elif fault=="calibration": a["calibration_sha256"]="a"*64
    elif fault=="aggregate": s["stop_line_crossings"]=[]
    elif fault=="counts": s["frames"][1]["crossing_observation"]["counts"]["north"]=2
    elif fault=="interval": s["stop_line_crossings"][0]["time_interval_s"]=[.1,1]
    elif fault=="window_extent": a["windows"][0]["end_s"]=4
    elif fault=="overlap": a["windows"].append({**a["windows"][0],"window_id":"overlap"})
    elif fault=="nonfinite": a["events"][0]["time_s"]=float("nan")
    elif fault=="duplicate_label": a["events"].append(copy.deepcopy(a["events"][0]))
    else: a["windows"][0]["exhaustive"]=False
    with pytest.raises((ValueError,ValidationError)): score(s,a,p,h)


def test_predictions_outside_labeled_windows_are_reported_unscored():
    s,a,p,h=fixture()
    a["windows"][0]["start_s"]=1
    a["events"]=a["events"][1:]
    result=score(s,a,p,h)
    assert result["unscored_prediction_indices"]==[0]
    assert result["metrics"]["false_positive"]==0 and result["metrics"]["false_negative"]==1


def test_report_reconstructs_and_refuses_overwrite_or_tampering(tmp_path):
    s,a,p,_=fixture()
    for name,data in [("session",s),("annotations",a),("protocol",p)]:
        (tmp_path/f"{name}.json").write_text(json.dumps(data))
    video=tmp_path/"fixture.avi"
    video.write_bytes(b"synthetic fixture bytes; not a decoded video")
    output=tmp_path/"report"
    args=[tmp_path/"session.json",tmp_path/"annotations.json",tmp_path/"protocol.json",video,output]
    report=run(*args)
    assert verify(output,video)["verified"]
    with pytest.raises(FileExistsError): run(*args)
    report["metrics"]["recall"]=1
    (output/"report.json").write_text(json.dumps(report))
    with pytest.raises(ValueError,match="reconstruct"): verify(output,video)


def test_legacy_random_generator_cannot_create_results(tmp_path):
    with pytest.raises(RuntimeError,match="fabricated"):
        run_cv_validation_evaluation(output_dir=tmp_path)
    assert list(tmp_path.iterdir())==[]


def test_equal_counts_do_not_prove_object_identity_or_timing():
    report=CVStateValidator().evaluate([{"lane_counts":{"north_straight":2}}],[{"lane_counts":{"north_straight":2}}])
    assert report.count_mae==0
    assert report.precision is report.recall is report.arrival_time_mae_s is report.uncertainty_error_correlation is None
