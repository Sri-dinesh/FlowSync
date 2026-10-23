"""The optional gate must not weaken hard-stale failover or physical guards."""
import copy
import json
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from research.calibration.fit_benefit_gate import fit, samples
from research.evaluation.evaluate_validation import benefit_gate_variants
from research.uncertainty.benefit_gate import FEATURE_NAMES, FallbackBenefitGate, observable_features
from server.app.controllers.base import ControllerContext
from server.app.controllers.flowsync_uq import FlowSyncUQController
from server.app.controllers.supervisor import ControllerSupervisor


def gate_file(tmp_path, intercept=-10.):
    model = dict(version="fallback_benefit_logistic_v1", feature_names=FEATURE_NAMES,
                 mean=[0.]*8, scale=[1.]*8, coefficients=[0.]*8, intercept=intercept,
                 threshold=.5, calibration_sha256="calibration", checkpoint_hashes=["checkpoint"])
    path = tmp_path / "gate.json"
    path.write_text(json.dumps(model))
    return path


def controller(tmp_path, intercept=-10., enabled=True):
    policy = Mock(_checkpoint_hash="checkpoint")
    policy.act.return_value = 0
    policy.get_diagnostics.return_value = {}
    estimator = Mock(calibration_hash="calibration")
    estimator.compute.return_value = SimpleNamespace(score=.9, features=SimpleNamespace(to_dict=lambda: {}))
    fallback = Mock(name="fallback")
    fallback.act.return_value = 1
    c = FlowSyncUQController(d3qn_controller=policy, fallback_controller=fallback,
        uncertainty_estimator=estimator, benefit_gate_path=str(gate_file(tmp_path, intercept)),
        supervisor=ControllerSupervisor(min_dwell_steps=4, recovery_window_steps=2), enable_fallback=enabled)
    c.reset(1)
    return c


def tick(c, score=.9, age=0., **context):
    c.uncertainty_estimator.compute.return_value.score = score
    return c.act(np.zeros(28), ControllerContext(0, time_in_phase=10.,
                  extra_telemetry={"observation_age_ms": age}, **context))


def test_veto_latched_and_reset_after_consecutive_low_ticks(tmp_path):
    c = controller(tmp_path)
    for _ in range(20):
        tick(c)
    assert c._gate_evaluations == c._gate_vetoes == 1
    assert c.supervisor.total_fallback_steps == 0
    tick(c, .1)
    tick(c)
    assert c._gate_evaluations == 1
    tick(c, .1)
    tick(c, .1)
    tick(c)
    assert c._gate_evaluations == 2
    c.reset(1)
    assert c._gate_evaluations == 0 and c._gate_allow is None


def test_stale_bypasses_veto_and_active_fallback_retains_dwell(tmp_path):
    c = controller(tmp_path)
    tick(c)
    tick(c, age=1000.)
    assert c._last_authority.value == "fallback_active"
    for _ in range(3):
        tick(c, .1)
        assert c._last_authority.value == "fallback_active"
    tick(c, .1)
    assert c._last_authority.value == "rl_active"


def test_gate_cannot_disable_shield(tmp_path):
    c = controller(tmp_path)
    assert tick(c, phase_starvation_times={1: 50.}) == 1
    assert c.get_diagnostics()["was_overridden"]


def test_disabled_fallback_does_not_evaluate_gate(tmp_path):
    c = controller(tmp_path, enabled=False)
    tick(c, age=1000.)
    assert c._gate_evaluations == 0
    assert c._last_authority.value == "rl_active"


def test_allow_all_gate_matches_ungated_authority_and_actions(tmp_path):
    c = controller(tmp_path, intercept=10.)
    original = copy.deepcopy(c)
    original.benefit_gate = None
    for score, age in [(.1, 0), (.9, 0), (.1, 0), (.9, 0), (.1, 1000)] + [(.1, 0)]*10:
        assert tick(c, score, age) == tick(original, score, age)
        assert c.supervisor.get_audit_summary() == original.supervisor.get_audit_summary()


def test_invalid_features_preserve_original_supervisor(tmp_path):
    c = controller(tmp_path)
    tick(c, movement_queues={"north_left": float("nan")})
    assert c._gate_probability is None and c._gate_allow
    assert c._last_authority.value == "fallback_active"


@pytest.mark.parametrize("field,value", [("scale", [0.]*8), ("coefficients", [1.]*7),
                                           ("intercept", float("nan")), ("threshold", 1.)])
def test_reject_invalid_gate(tmp_path, field, value):
    path = gate_file(tmp_path)
    model = json.loads(path.read_text())
    model[field] = value
    path.write_text(json.dumps(model))
    with pytest.raises(ValueError):
        FallbackBenefitGate(path)


@pytest.mark.parametrize("field,value", [("calibration_sha256", "wrong"), ("checkpoint_hashes", ["wrong"])])
def test_reject_mismatched_provenance(tmp_path, field, value):
    path = gate_file(tmp_path)
    model = json.loads(path.read_text())
    model[field] = value
    path.write_text(json.dumps(model))
    with pytest.raises(ValueError, match="recorded uncertainty|checkpoint family"):
        FlowSyncUQController(d3qn_controller=Mock(_checkpoint_hash="checkpoint"),
            uncertainty_estimator=Mock(calibration_hash="calibration"), benefit_gate_path=str(path))


def training_data():
    manifest = dict(arguments=dict(split="train", seeds=[91001]), feature_names=FEATURE_NAMES,
        planned_runs=1, scenario_hashes={"train_a": "scenario"}, faults=[dict(name="mixed")],
        choices=[dict(sha256="checkpoint")])
    events = []
    for i in range(20):
        branch = dict(incremental_delay_vehicle_seconds=10., upstream_max_wait_s=20.,
                      signal_violations=0, signal_samples=200, arrival_trace_hash="paired")
        events.append(dict(kind="fallback_entry", stale_observation_failover=False, horizon_steps=200,
            intervention_kept=branch, intervention_omitted={**branch, "incremental_delay_vehicle_seconds": 11. if i < 10 else 9.},
            observable_features=[float(i)]*8))
    return manifest, [dict(split="train", scenario="train_a", scenario_hash="scenario", seed=91001,
                          checkpoint_hash="checkpoint", fault=dict(name="mixed"), events=events)]


def test_training_fit_and_runtime_agree(tmp_path):
    x, y = samples(*training_data())
    model = fit(x, y)
    path = tmp_path/"fitted.json"
    path.write_text(json.dumps(model))
    gate = FallbackBenefitGate(path)
    assert gate.predict(x[0]) > .5 > gate.predict(x[-1])
    assert model["training_samples"] == 20


@pytest.mark.parametrize("corruption", ["validation", "duplicate", "unpaired", "nan", "coverage", "few_positive"])
def test_reject_invalid_training_data(corruption):
    manifest, rows = training_data()
    if corruption == "validation":
        rows[0]["split"] = "validation"
    elif corruption == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
        manifest["planned_runs"] = 2
    elif corruption == "unpaired":
        rows[0]["events"][0]["intervention_kept"]["arrival_trace_hash"] = "different"
    elif corruption == "nan":
        rows[0]["events"][0]["intervention_kept"]["upstream_max_wait_s"] = float("nan")
    elif corruption == "coverage":
        rows[0]["events"][0]["intervention_kept"]["signal_samples"] = 199
    else:
        rows[0]["events"].pop()
    with pytest.raises(ValueError):
        samples(manifest, rows)


def test_features_do_not_use_offline_truth():
    context = ControllerContext(0, movement_queues={"north_left": 3}, phase_starvation_times={2: 12.})
    expected = observable_features(context, .8)
    context.extra_telemetry["phase_wait_truth"] = {2: 9999.}
    assert observable_features(context, .8) == expected


def test_comparison_has_exactly_three_matched_shielded_variants():
    variants = benefit_gate_variants("calibration.json", "gate.json")
    assert set(variants) == {"uq_shield_only", "uq_full", "uq_gated"}
    for name, options in variants.values():
        assert name == "flowsync_uq" and options["enable_shield"]
        assert options["calibration_path"] == "calibration.json"
    assert variants["uq_shield_only"][1]["enable_fallback"] is False
    assert "benefit_gate_path" not in variants["uq_full"][1]
    with pytest.raises(ValueError):
        benefit_gate_variants(None, "gate.json")


def test_real_rollout_allow_all_gate_preserves_original_trajectory(tmp_path):
    import torch
    from research.experiments.engine import ExperimentRunner
    from research.noise.fault_injector import FaultProfile, PerceptionFaultInjector
    from research.scenarios.scenario_schema import ScenarioConfig
    from research.training.train_policy import file_hash
    from research.uncertainty.estimator import UncertaintyFeatures
    from server.app.rl.dqn_agent import DQNAgent

    torch.set_num_threads(1)
    checkpoint = tmp_path/"checkpoint.pt"
    torch.save(DQNAgent().get_checkpoint_state(), checkpoint)
    calibration = tmp_path/"calibration.json"
    calibration.write_text(json.dumps(dict(version="synthetic_error_logistic_v1",
        feature_names=list(UncertaintyFeatures().to_dict()), mean=[0.]*7, scale=[1.]*7,
        coefficients=[0.]*7, intercept=10., threshold_high=.45, threshold_low=.25)))
    path = gate_file(tmp_path, intercept=10.)
    model = json.loads(path.read_text())
    model.update(checkpoint_hashes=[file_hash(checkpoint)], calibration_sha256=file_hash(calibration))
    path.write_text(json.dumps(model))
    scenario = ScenarioConfig("val_gate_parity", "validation", "Gate parity", duration_steps=600)
    kwargs = dict(checkpoint_path=str(checkpoint), calibration_path=str(calibration))
    results = [ExperimentRunner().run(FlowSyncUQController(**kwargs, benefit_gate_path=gate), scenario, 21001,
               record_trajectory=False, fault_injector=PerceptionFaultInjector(FaultProfile(miss_rate=.2), seed=111001))
               for gate in (None, str(path))]
    for field in ("avg_delay", "p95_delay", "total_vehicles_passed", "arrival_trace_hash",
                  "fallback_steps", "fallback_activations", "shield_interventions", "safety_samples"):
        assert getattr(results[0], field) == getattr(results[1], field)
    assert results[1].controller_diagnostics["benefit_gate_evaluations"] == 1
    assert results[1].controller_diagnostics["benefit_gate_hash"] == file_hash(path)
