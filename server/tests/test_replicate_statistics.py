import numpy as np
import json
import pytest
from research.evaluation.evaluate_replicates import crossed_bootstrap, evaluation_seeds
from research.evaluation.evaluate_validation import supervisor_variants
from research.audits.check_horizon import extend_scenario
from research.scenarios.scenario_schema import ScenarioConfig, DemandProfile


def test_crossed_bootstrap_constant_and_seed_reproducibility():
    constant = crossed_bootstrap(np.full((3, 20, 7), 2.5), draws=100)
    assert constant["bootstrap_ci95_s"] == [2.5, 2.5]
    assert constant["training_replicates"] == 3
    data = np.random.default_rng(5).normal(size=(3, 20, 7))
    assert crossed_bootstrap(data, draws=100) == crossed_bootstrap(data, draws=100)


def test_bootstrap_rejects_non_crossed_or_missing_data():
    with pytest.raises(ValueError):
        crossed_bootstrap(np.zeros((20, 7)))
    with pytest.raises(ValueError):
        crossed_bootstrap(np.full((3, 20, 7), np.nan))


def test_fresh_seed_range_rejects_reuse(tmp_path):
    prior = tmp_path / "manifest.json"
    prior.write_text(json.dumps({"traffic_seeds": [51001, 51002]}))
    assert evaluation_seeds(61001, 20, [prior]) == list(range(61001, 61021))
    with pytest.raises(ValueError, match="overlap"):
        evaluation_seeds(51000, 3, [prior])
    with pytest.raises(ValueError):
        evaluation_seeds(-1, 20)
    with pytest.raises(ValueError):
        evaluation_seeds(61001, 0)


def test_supervisor_factorial_explicitly_varies_both_components():
    variants = supervisor_variants("calibration.json")
    uq = [options for controller, options in variants.values() if controller == "flowsync_uq"]
    assert len(uq) == 4
    assert {(v["enable_shield"], v["enable_fallback"]) for v in uq} == {
        (False, False), (False, True), (True, False), (True, True)}
    assert all(v["calibration_path"] == "calibration.json" for v in uq)
    assert variants["d3qn"] == ("d3qn", {})
    assert variants["max_pressure"] == ("max_pressure", {})


def test_horizon_extension_scales_events_without_mutating_original():
    original = ScenarioConfig("test_duration", "test", "Duration", duration_steps=1500,
                              demand_profile=DemandProfile(incident_events=[
                                  {"start_step": 500, "end_step": 1000, "direction": "north", "capacity_factor": .5}]))
    extended = extend_scenario(original)
    assert extended.duration_steps == 6000
    assert extended.demand_profile.incident_events[0]["start_step"] == 2000
    assert original.demand_profile.incident_events[0]["start_step"] == 500
    assert extended.compute_hash() != original.compute_hash()
