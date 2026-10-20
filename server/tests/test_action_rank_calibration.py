import copy

import numpy as np
import pytest

from research.calibrate_action_rank import (
    PARENTS, ROLES, calibrate, choose, fit_point, probe_predictions,
    residual_margin, role_arrays, summarize,
)


def rows(role, parent=101):
    result = []
    for seed in ROLES[role]:
        base = dict(incremental_delay_vehicle_seconds=20., vehicles_passed=3,
                    upstream_max_wait_s=10.)
        event = dict(step=200, phase=0, phase_age=20., policy_proposal=0,
                     policy_observation=[0.] * 36, q_values=[0.] * 4,
                     mask=[True, False, True, True],
                     all_action_branches=[
                         dict(proposal=a, first_execution=a, outcome=dict(
                             base, incremental_delay_vehicle_seconds=20. - a))
                         for a in (0, 2, 3)])
        result.append(dict(split="train", data_role=role, training_seed=parent,
                           checkpoint_hash="fixture", seed=seed, scenario="train_fixture",
                           fault=dict(name="clean"), events=[event]))
    paired = copy.deepcopy(result)
    for row in paired:
        row["fault"]["name"] = "validation_mixed"
    return result + paired


def test_fit_is_role_bound_deterministic_and_clustered_by_traffic():
    fit = rows("fit")
    first = fit_point(fit, 101, "fixture")
    assert first == fit_point(fit, 101, "fixture")
    assert first["fit_traffic_seeds"] == list(ROLES["fit"])
    assert first["fit_examples"] == 24
    assert first["weight_group"] == "whole_traffic_seed"
    with pytest.raises(ValueError, match="Wrong role"):
        fit_point(rows("calibration"), 101, "fixture")
    fit[0]["seed"] = ROLES["probe"][0]
    with pytest.raises(ValueError, match="Incomplete or leaking"):
        fit_point(fit, 101, "fixture")


def test_group_margin_uses_worst_error_across_actions_targets_and_faults():
    groups = np.repeat(np.arange(10), 3)
    point = np.zeros((30, 3))
    actual = np.zeros_like(point)
    actual[-1, 1] = -7.
    margin, scores, rank = residual_margin(point, actual, groups)
    assert rank == 10 and margin == 7.
    assert scores[9] == 7.
    # Duplicating the same traffic group's observations does not change margin.
    more = residual_margin(np.concatenate([point, point[-3:]]),
                           np.concatenate([actual, actual[-3:]]),
                           np.concatenate([groups, groups[-3:]]))
    assert more == (margin, scores, rank)
    with pytest.raises(ValueError, match="Insufficient calibration"):
        residual_margin(point[:9], actual[:9], groups[:9])


def test_bad_calibration_arrays_rejected_and_margin_nonnegative():
    point = np.zeros((10, 3))
    margin, _, _ = residual_margin(point, np.ones_like(point), np.arange(10))
    assert margin == 0.
    point[0, 0] = np.nan
    with pytest.raises(ValueError, match="Invalid calibration"):
        residual_margin(point, np.ones_like(point), np.arange(10))


def test_calibration_does_not_refit_point_and_probe_cannot_calibrate():
    model = fit_point(rows("fit"), 101, "fixture")
    original = copy.deepcopy(model)
    calibrated = calibrate(model, rows("calibration"))
    assert model == original
    assert calibrated["point"] == original["point"]
    assert calibrated["scale"] == original["scale"]
    assert calibrated["calibration_traffic_seeds"] == list(ROLES["calibration"])
    with pytest.raises(ValueError, match="Wrong role"):
        calibrate(model, rows("probe"))
    with pytest.raises(ValueError, match="Already calibrated"):
        calibrate(calibrated, rows("calibration"))


def test_probe_requires_frozen_model_and_never_refits():
    model = fit_point(rows("fit"), 101, "fixture")
    with pytest.raises(ValueError, match="frozen calibrated"):
        probe_predictions(model, rows("probe"))
    calibrated = calibrate(model, rows("calibration"))
    before = copy.deepcopy(calibrated)
    alternatives, decisions = probe_predictions(calibrated, rows("probe"))
    assert calibrated == before
    assert len(alternatives) == 8 and len(decisions) == 8
    with pytest.raises(ValueError, match="Wrong role"):
        role_arrays(rows("probe"), "probe", 202, "fixture")


def test_abstention_cannot_pass_activity_screen():
    alternatives, decisions = [], []
    for parent in PARENTS:
        model = fit_point(rows("fit", parent), parent, "fixture")
        model = calibrate(model, rows("calibration", parent))
        model["normalized_margin"] = 1000.
        a, d = probe_predictions(model, rows("probe", parent))
        alternatives.extend(a)
        decisions.extend(d)
    report = summarize(alternatives, decisions)
    assert report["checks"]["all_probe_traffic_groups_covered"]
    assert report["checks"]["no_selected_harm"]
    assert not report["checks"]["every_parent_active"]
    assert not report["continue_to_rollout_validation"]
    assert not report["publication_ready"] and not report["dqn_retrained"]


def test_selection_constraints_and_tie_break_are_unchanged():
    assert choose({1: [2., 0., 0.], 2: [2., 0., 0.]}, 0) == 1
    assert choose({1: [100., -1., 0.], 2: [100., 0., -2.]}, 0) == 0
