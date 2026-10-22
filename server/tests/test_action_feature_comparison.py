import copy
import itertools

import numpy as np
import pytest

from research.analysis.compare_action_features import (
    PARENTS, RIDGE, ROLES, TARGET_SCALE, VARIANTS, decision_rows, extract,
    features, fit_fold, predict, summarize,
)


def event():
    return dict(policy_observation=np.linspace(0., 1., 36).tolist(),
                phase=0, phase_age=20., policy_proposal=0,
                q_values=[1., 2., 3., 4.])


def test_features_are_observable_only_and_parent_contrast_is_zero():
    e = event()
    for variant, dimension in (("compact", 8), ("full_state", 160)):
        x = features(e, 2, variant)
        assert x.shape == (dimension,)
        assert np.array_equal(features(e, 0, variant), np.zeros(dimension))
        altered = dict(e, all_action_branches=[{"secret_outcome": 1e9}],
                       seed=999, checkpoint_hash="irrelevant")
        assert np.array_equal(features(altered, 2, variant), x)
    assert np.array_equal(features(e, 2, "full_state")[:8], features(e, 2, "compact"))
    with pytest.raises(ValueError):
        features(e, 2, "unknown")


def test_whole_excluded_seed_cannot_affect_fit_or_normalization():
    rng = np.random.default_rng(10)
    groups = np.repeat(ROLES["fit"], [2, 3, 4, 5, 6, 7])
    x, y = rng.normal(size=(len(groups), 8)), rng.normal(size=(len(groups), 3))
    excluded = ROLES["fit"][0]
    model = fit_fold(x, y, groups, excluded)
    changed_x, changed_y = x.copy(), y.copy()
    changed_x[groups == excluded] = 1e6
    changed_y[groups == excluded] = -1e6
    assert fit_fold(changed_x, changed_y, groups, excluded) == model
    assert excluded not in model["train_seeds"]
    assert model["train_examples"] == len(groups) - 2
    train = groups != excluded
    weights = np.array([1 / np.sum(groups[train] == g) for g in groups[train]])
    scale = np.maximum(np.sqrt(np.average(x[train] ** 2, axis=0, weights=weights)), .05)
    weights /= weights.mean()
    z = x[train] / scale
    reference = np.linalg.solve(
        z.T @ np.diag(weights) @ z + RIDGE * np.eye(8),
        z.T @ np.diag(weights) @ (y[train] / TARGET_SCALE))
    np.testing.assert_allclose(model["point"], reference, atol=1e-12)
    np.testing.assert_allclose(predict(model, x), (x / scale) @ reference * TARGET_SCALE)
    with pytest.raises(ValueError, match="Invalid fitting fold"):
        fit_fold(x[train], y[train], groups[train], excluded)


@pytest.mark.parametrize("field,value", [
    ("split", "test"), ("data_role", "probe"), ("training_seed", 202),
    ("seed", 95201),
])
def test_extraction_rejects_other_roles_parents_and_traffic(field, value):
    row = dict(split="train", data_role="fit", training_seed=101,
               seed=95001, checkpoint_hash="fixture", events=[])
    row[field] = value
    with pytest.raises(ValueError, match="fitting role"):
        extract([row], 101, "compact")


def predictions():
    rows = []
    for variant, parent, seed in itertools.product(VARIANTS, PARENTS, ROLES["fit"]):
        rows.append(dict(variant=variant, training_seed=parent, traffic_seed=seed,
                         scenario="fixture", fault="clean", step=200, parent=0,
                         action=1, executed_change=True, actual=[4., 1., 1.],
                         point=[2., 0., 0.] if variant == "compact" else [3., 1., 1.]))
    return rows


def test_success_requires_both_prediction_and_decision_checks():
    rows = predictions()
    report = summarize(rows, decision_rows(rows))
    assert report["continue_to_rollout_validation"]
    assert report["folds"] == 36
    assert not report["publication_ready"]
    assert not any(report[k] for k in (
        "calibration_access", "probe_access", "validation_access", "final_test_access"))
    # Better numerical errors alone cannot pass with no changes.
    for row in rows:
        row["actual"] = [0., 0., 0.]
        row["point"] = [0., 0., 0.]
    report = summarize(rows, decision_rows(rows))
    assert not report["continue_to_rollout_validation"]
    assert not report["checks"]["every_parent_active_and_beneficial"]
    with pytest.raises(ValueError, match="Incomplete prediction cells"):
        summarize(rows[:-1], decision_rows(rows[:-1]))


def test_duplicate_alternatives_rejected_and_abstention_not_beneficial():
    rows = predictions()[:1]
    with pytest.raises(ValueError, match="duplicate alternatives"):
        decision_rows(rows + copy.deepcopy(rows))
    rows[0]["point"] = [100., -1., 1.]
    decision = decision_rows(rows)[0]
    assert decision["choice"] == 0
    assert decision["actual"] == [0., 0., 0.]
    assert not decision["executed_change"]
    assert not decision["qualified"]
    assert not decision["harmful"]
