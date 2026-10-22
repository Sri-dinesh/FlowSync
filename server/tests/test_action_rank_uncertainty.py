import copy

import numpy as np
import pytest

from research.policies.action_rank_policy import BOOTSTRAPS, FEATURES, RankingModel, TARGET_SCALE
from research.audits.audit_action_rank_uncertainty import aggregate, score_rows, summarize


def fixture():
    point = np.zeros((8, 3))
    point[6, 0] = .25  # Always predicts +10 vehicle-seconds for left phase.
    model = RankingModel(dict(
        version="action_rank_ridge_v1", features=list(FEATURES),
        parent_sha256="parent", scale=[1.] * 8, point=point.tolist(),
        ensemble=np.tile(point, (BOOTSTRAPS, 1, 1)).tolist(),
        target_scale=TARGET_SCALE.tolist()))
    base = dict(incremental_delay_vehicle_seconds=20., vehicles_passed=3,
                upstream_max_wait_s=10., signal_samples=400,
                signal_violations=0, arrival_trace_hash="paired")
    event = dict(
        step=200, policy_proposal=0, phase=0, phase_age=20.,
        policy_observation=[0.] * 36, q_values=[0.] * 4,
        mask=[True, False, True, False], horizon_steps=400,
        all_action_branches=[
            dict(proposal=0, outcome=base),
            dict(proposal=2, outcome=dict(base, incremental_delay_vehicle_seconds=25.))])
    row = dict(split="train", seed=94002, training_seed=101, scenario="train_fixture",
               checkpoint_hash="parent", fault=dict(name="clean"),
               signal_samples=1200, signal_violations=0, events=[event])
    return row, {101: model}


def test_identical_bootstraps_do_not_imply_accurate_predictions():
    row, models = fixture()
    scored, decisions = score_rows([row], models)
    report = summarize(scored, decisions, [row])
    delay = report["pooled"]["metrics"]["delay_vehicle_seconds"]
    assert delay["mae"] == 15.
    assert delay["mean_bootstrap_std"] == 0.
    assert delay["lower_bound_coverage"] == 0.
    assert delay["spread_absolute_error_correlation"] is None
    assert report["selections"]["uncertain"]["delay_harm_over_one"] == 1
    assert not report["model_changed"] and not report["validation_access"]


def test_fault_pairs_share_cluster_and_ties_are_covered():
    row, models = fixture()
    second = copy.deepcopy(row)
    second["fault"]["name"] = "validation_mixed"
    scored, decisions = score_rows([row, second], models)
    report = summarize(scored, decisions, [row, second])
    assert len(report["clusters"]) == 1
    assert report["labelled_decision_gates"] == 2
    assert report["pooled"]["metrics"]["throughput_vehicles"]["lower_bound_coverage"] == 1.
    assert report["pooled"]["simultaneous_lower_coverage"] == 0.


@pytest.mark.parametrize("defect", [
    "split", "seed", "parent", "source_samples", "missing_action",
    "duplicate_action", "arrival", "branch_samples", "nonfinite", "conflict",
])
def test_invalid_or_leaking_data_rejected(defect):
    row, models = fixture()
    event = row["events"][0]
    branches = event["all_action_branches"]
    if defect == "split":
        row["split"] = "validation"
    elif defect == "seed":
        row["seed"] = 94001
    elif defect == "parent":
        row["checkpoint_hash"] = "other"
    elif defect == "source_samples":
        row["signal_samples"] = 0
    elif defect == "missing_action":
        branches.pop()
    elif defect == "duplicate_action":
        branches[1]["proposal"] = 0
    elif defect == "arrival":
        branches[1]["outcome"]["arrival_trace_hash"] = "unpaired"
    elif defect == "branch_samples":
        branches[1]["outcome"]["signal_samples"] = 399
    elif defect == "nonfinite":
        branches[1]["outcome"]["upstream_max_wait_s"] = float("nan")
    elif defect == "conflict":
        branches[1]["outcome"]["signal_violations"] = 1
    with pytest.raises(ValueError):
        score_rows([row], models)


def test_spread_error_association_is_descriptive():
    rows = [dict(actual=[v, 0., 0.], point=[0.] * 3, lower=[0.] * 3,
                 spread=[v, 0., 0.]) for v in (1., 2., 3.)]
    report = aggregate(rows)
    assert report["metrics"]["delay_vehicle_seconds"]["spread_absolute_error_correlation"] == 1.
    assert report["metrics"]["throughput_vehicles"]["spread_absolute_error_correlation"] is None
