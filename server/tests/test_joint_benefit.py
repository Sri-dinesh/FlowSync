import copy

import numpy as np
import pytest

from research.analysis.compare_joint_benefit import (
    ARMS, choose_joint, fit_fold, fit_pair, logistic, predict, predict_source,
    read_fit, sigmoid, summarize,
)
from research.policies.averaged_label_model import cells, configuration
from research.training.train_policy import load_split
from server.tests.test_averaged_label_model import row


def test_solver_is_deterministic_converged_and_class_balanced():
    rng = np.random.default_rng(5)
    x = rng.normal(size=(90, 8))
    y = (x[:, 0] + x[:, 1] > .5).astype(float)
    weight = np.linspace(.5, 2., len(x))
    model = logistic(x, y, weight)
    assert model == logistic(x, y, weight)
    assert model["gradient_max"] <= 1e-7 and model["converged"]
    balanced = weight.copy()
    for label in (0., 1.):
        balanced[y == label] /= balanced[y == label].sum()
    balanced /= balanced.mean()
    beta = np.array(model["coefficients"])
    design = np.column_stack((x, np.ones(len(x))))
    gradient = design.T @ (balanced * (sigmoid(design @ beta) - y))
    gradient[:8] += 10 * beta[:8]
    np.testing.assert_allclose(gradient, 0., atol=1e-7)
    with pytest.raises(RuntimeError, match="converge"):
        logistic(x, y, weight, max_iterations=0)


def test_intercept_is_unpenalized_and_sigmoid_stable():
    # A shared nonzero offset must be absorbed by the unpenalized intercept.
    x = np.zeros((60, 8))
    x[:, 0] = np.linspace(-1, 2, 60)
    y = (x[:, 0] > .8).astype(float)
    first = logistic(x, y, np.ones(60))
    shifted = x.copy()
    shifted[:, 0] += 4.
    second = logistic(shifted, y, np.ones(60))
    a, b = np.array(first["coefficients"]), np.array(second["coefficients"])
    np.testing.assert_allclose(a[:8], b[:8], atol=1e-7)
    assert b[-1] == pytest.approx(a[-1] - 4 * a[0], abs=1e-7)
    np.testing.assert_array_equal(sigmoid([-1e6, 0., 1e6]), [0., .5, 1.])


@pytest.mark.parametrize("label", [0., 1.])
def test_single_class_fallback_explicit(label):
    model = logistic(np.zeros((4, 8)), np.full(4, label), np.ones(4))
    assert model["constant"] == label and model["coefficients"] is None
    assert model["converged"] and model["iterations"] == 0


def test_scaling_precedes_class_balancing_and_ridge_matches_reference():
    rng = np.random.default_rng(4)
    x = rng.normal(size=(12, 8))
    x[:, 7] = 0.
    target = np.column_stack((np.arange(12) - 1., np.ones(12), np.zeros(12)))
    groups = [96301] * 2 + [96302] * 4 + [96303] * 6
    pair = fit_pair(x, target, groups)
    w = np.array([1/2] * 2 + [1/4] * 4 + [1/6] * 6)
    scale = np.maximum(np.sqrt(np.average(x*x, axis=0, weights=w)), .05)
    assert pair["regression"]["scale"] == pair["joint"]["scale"] == scale.tolist()
    z, w = x / scale, w / w.mean()
    expected = np.linalg.solve(z.T @ (w[:, None] * z) + 10*np.eye(8),
                               z.T @ (w[:, None] * (target / [40., 1., 40.])))
    np.testing.assert_array_equal(pair["regression"]["point"], expected)
    assert "NOT calibrated" in pair["joint"]["score_semantics"]


def test_held_out_rows_never_enter_fit_scaling_or_prediction():
    rows = [row(seed) for seed in configuration()["fit_seeds"]]
    pair = fit_fold(rows, 101, 96304)
    before = predict_source(rows[-1], pair)
    modified = copy.deepcopy(rows)
    modified[-1]["events"][0]["policy_observation"] = [1e9] * 36
    for event in modified[-1]["events"]:
        event["all_action_branches"] = "unreadable outcomes"
        event["branch_diagnostic"] = "unreadable outcomes"
    assert fit_fold(modified, 101, 96304) == pair
    modified[-1]["events"][0]["policy_observation"] = rows[-1]["events"][0]["policy_observation"]
    assert predict_source(modified[-1], pair) == before
    assert pair["joint"]["fit_seeds"] == [96301, 96302, 96303]
    with pytest.raises(ValueError, match="mismatch"):
        predict_source(rows[0], pair)


def test_joint_selection_strict_threshold_tie_and_invalid_score():
    assert choose_joint({1: .5, 2: .3}, 0) == 0
    assert choose_joint({2: .6, 1: .6}, 0) == 1
    assert choose_joint({1: .6, 2: .7}, 0) == 2
    with pytest.raises(ValueError):
        choose_joint({1: float("nan")}, 0)


def test_inactive_or_incomplete_cannot_pass():
    config = configuration()
    names = [s.scenario_id for s in load_split("train")]
    scores = [dict(training_seed=p, scenario=n, seed=s, arms={a: dict(cases=16,
        changed_cases=0, executed_change_cases=0, qualified_cases=0, harmful_cases=0,
        mean_gain=[0., 0., 0.]) for a in ARMS}) for p, n, s in cells(config, names, "fit")]
    folds = [(p, s) for p in config["parents"] for s in config["fit_seeds"]]
    result = summarize(scores, folds)
    assert result["complete"] and result["fitted_models"] == 24
    assert not result["continue_to_fresh_source_pilot"] and not result["publication_ready"]
    assert not summarize(scores[:-1], folds)["complete"]
    assert not summarize(scores, folds[:-1])["complete"]
    with pytest.raises(ValueError, match="cells"):
        summarize(scores + scores[:1], folds)


def test_reject_nonfinite_bad_shape_and_wrong_dataset(tmp_path):
    with pytest.raises(ValueError):
        fit_pair([[0.] * 7], [[0.] * 3], [1])
    with pytest.raises(ValueError):
        logistic(np.zeros((2, 8)), [0., np.nan], [1., 1.])
    pair = fit_pair(np.zeros((2, 8)), np.zeros((2, 3)), [1, 2])
    with pytest.raises(ValueError):
        predict(pair["joint"], [float("nan")] * 8)
    (tmp_path / "fit.jsonl").write_text("{}\n")
    with pytest.raises(ValueError, match="prespecified"):
        read_fit(tmp_path)
