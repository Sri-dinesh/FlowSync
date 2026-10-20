import json
import numpy as np
import pytest

from research.calibrate_uncertainty import binary_metrics, fit_calibration, predict, select_threshold
from research.uncertainty.estimator import PerceptionUncertaintyEstimator
from server.app.controllers.flowsync_uq import FlowSyncUQController


def test_fitted_artifact_roundtrip_and_supervisor_thresholds(tmp_path):
    rng = np.random.default_rng(2)
    x = rng.random((300, 7))
    y = (x[:, 2] > .5).astype(int)
    fitted = fit_calibration(x, y)
    fitted.update(threshold_high=.7, threshold_low=.3)
    path = tmp_path / "calibration.json"
    path.write_text(json.dumps(fitted))
    estimator = PerceptionUncertaintyEstimator(calibration_path=str(path))
    score = estimator.compute(np.zeros(12))
    assert score.score == pytest.approx(predict(fitted, [score.features.to_array()])[0])
    assert estimator.calibration_hash
    ctrl = FlowSyncUQController(calibration_path=str(path))
    assert ctrl.threshold_high == .7
    assert ctrl.supervisor.threshold_high == .7
    assert ctrl.get_diagnostics()["uncertainty_calibration_hash"] == estimator.calibration_hash


def test_calibration_requires_both_classes_and_valid_schema(tmp_path):
    with pytest.raises(ValueError):
        fit_calibration(np.zeros((10, 7)), np.zeros(10))
    p = tmp_path / "bad.json"
    p.write_text('{"version":"wrong"}')
    with pytest.raises(ValueError, match="schema"):
        PerceptionUncertaintyEstimator(calibration_path=str(p))


def test_ece_includes_probability_one_and_auc_is_defined_only_with_classes():
    report = binary_metrics([0, 0], [1., 1.])
    assert report["ece"] == 1.
    assert report["roc_auc"] is None


def test_threshold_obeys_false_positive_constraint():
    y = np.array([0]*10 + [1]*10)
    scores = np.r_[np.linspace(.1,.6,10), np.linspace(.4,.95,10)]
    threshold = select_threshold(y, scores, .1)
    assert binary_metrics(y, scores, threshold)["false_positive_rate"] <= .1
