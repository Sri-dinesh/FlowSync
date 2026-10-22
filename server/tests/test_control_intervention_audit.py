import json

import pytest
import torch

from research.audits.audit_control_interventions import audit_run, fork_state, phase_wait_truth, rollout_branch
from research.experiments.engine import ExperimentRunner
from research.experiments.runtime import ObservedState, apply_scenario_step, build_environment
from research.noise.fault_injector import FaultProfile, PerceptionFaultInjector
from research.scenarios.scenario_schema import ScenarioConfig
from research.uncertainty.estimator import UncertaintyFeatures
from server.app.controllers.flowsync_uq import FlowSyncUQController
from server.app.controllers.safety_shield import SafetyShield
from server.app.rl.dqn_agent import DQNAgent
from server.app.simulation.intersection import Intersection
from server.app.simulation.vehicle import Vehicle


@pytest.fixture
def artifacts(tmp_path):
    torch.set_num_threads(1)
    checkpoint = tmp_path / "fixture.pt"
    agent = DQNAgent()
    with torch.no_grad():
        for parameter in agent.online_net.parameters():
            parameter.zero_()
        agent.online_net.advantage_stream[-1].bias[0] = 1.
    torch.save(agent.get_checkpoint_state(), checkpoint)
    calibration = tmp_path / "calibration.json"
    calibration.write_text(json.dumps({"version": "synthetic_error_logistic_v1",
        "feature_names": list(UncertaintyFeatures().to_dict()), "mean": [0.]*7,
        "scale": [1.]*7, "coefficients": [0.]*7, "intercept": -10.,
        "threshold_low": .25, "threshold_high": .45}))
    return checkpoint, calibration


def test_offline_wait_truth_includes_backlog_excludes_departing_vehicles():
    junction = Intersection()
    junction.lanes["north_left"] = [Vehicle("up", "north", "left", .4, 46., 0., "waiting"),
                                     Vehicle("out", "north", "left", .8, 99., .12, "moving")]
    junction.spawner._clock = 100.
    junction.spawner._pending["south_left"].append(20.)
    truth = phase_wait_truth(junction)[2]
    assert truth == {"upstream_vehicles": 2, "max_accumulated_wait_s": 80., "vehicles_waited_45s": 2}


def test_diagnostic_refuses_final_test_scenarios(artifacts):
    with pytest.raises(ValueError, match="final test"):
        audit_run(*artifacts, ScenarioConfig("test_no", "test", "No"), 1, FaultProfile())


@pytest.mark.parametrize("color", ["YELLOW", "RED"])
def test_clearance_overrides_are_counted_in_shield_audit(color):
    shield = SafetyShield()
    decision = shield.filter_action(2, 0, 1., color)
    assert decision.executed_action == 0
    assert decision.was_overridden
    metrics = shield.get_audit_metrics()
    assert metrics["total_overrides"] == 1
    assert metrics["override_counts_by_reason"] == {"clearance_interval_active": 1}
    shield.filter_action(0, 0, 1., color)
    assert shield.get_audit_metrics()["total_overrides"] == 1


def test_green_resets_phase_proxy_even_when_actual_vehicle_wait_is_large():
    env, _ = build_environment(ScenarioConfig("val_proxy", "validation", "Proxy"))
    env.reset(seed=21001)
    env.intersection.signal.current_phase = 2
    env.intersection.lanes["north_left"].append(Vehicle("old", "north", "left", .4, 60., 0., "waiting"))
    sensor = ObservedState()
    sensor.phase_waits[2] = 50.
    _, context = sensor.build(env, env._get_obs(), 0)
    assert context.phase_starvation_times[2] == 0
    assert phase_wait_truth(env.intersection)[2]["max_accumulated_wait_s"] == 60
    assert "not individual vehicle wait" in context.extra_telemetry["phase_wait_semantics"]


def test_missed_counts_reset_proxy_without_exposing_true_wait_to_controller():
    env, _ = build_environment(ScenarioConfig("val_proxy_miss", "validation", "Proxy"))
    env.reset(seed=21001)
    env.intersection.lanes["north_left"].append(Vehicle("old", "north", "left", .4, 60., 0., "waiting"))
    sensor = ObservedState()
    sensor.phase_waits[2] = 50.
    _, context = sensor.build(env, env._get_obs(), 0, PerceptionFaultInjector(FaultProfile(miss_rate=1), seed=1))
    assert context.phase_starvation_times[2] == 0
    assert context.movement_queues["north_left"] == 0
    assert phase_wait_truth(env.intersection)[2]["max_accumulated_wait_s"] == 60


def test_forks_are_independent_and_identical_actions_have_identical_cost(artifacts):
    scenario = ScenarioConfig("val_forks", "validation", "Forks", duration_steps=300)
    env, profile = build_environment(scenario)
    clean, _ = env.reset(seed=21001)
    sensor, injector = ObservedState(), PerceptionFaultInjector(FaultProfile(), seed=111001)
    controller = FlowSyncUQController(checkpoint_path=str(artifacts[0]), calibration_path=str(artifacts[1]))
    controller.reset(21001)
    apply_scenario_step(env.intersection, profile, scenario.demand_profile, 0)
    obs, ctx = sensor.build(env, clean, 0, injector)
    action = controller.act(obs, ctx)
    a, b = (fork_state(env, sensor, injector, controller) for _ in range(2))
    assert a[3].d3qn.agent is b[3].d3qn.agent is controller.d3qn.agent
    assert a[0].intersection.spawner is not b[0].intersection.spawner
    assert a[3].supervisor is not b[3].supervisor
    assert rollout_branch(a, scenario, 0, 200, action) == rollout_branch(b, scenario, 0, 200, action)
    assert env._env_step_count == 0
    assert injector.total_queries == 1


@pytest.mark.parametrize("fault", [FaultProfile(), FaultProfile(latency_ms=1000)])
def test_counterfactuals_do_not_change_source_trajectory(artifacts, fault):
    scenario = ScenarioConfig("val_audit_identity", "validation", "Identity", duration_steps=800)
    baseline = ExperimentRunner().run(FlowSyncUQController(checkpoint_path=str(artifacts[0]),
        calibration_path=str(artifacts[1])), scenario, 21001, record_trajectory=False,
        fault_injector=PerceptionFaultInjector(fault, seed=111001))
    audited = audit_run(*artifacts, scenario, 21001, fault, horizon=100, max_per_kind=1)
    assert audited["avg_delay"] == pytest.approx(baseline.avg_delay, abs=.001)
    assert audited["arrival_trace_hash"] == baseline.arrival_trace_hash
    assert audited["signal_samples"] == baseline.safety_samples == 800
    assert audited["signal_violations"] == baseline.executed_conflict_violations == 0
    assert audited["events"]
    branches = [e for e in audited["events"] if "intervention_kept" in e]
    assert branches
    for event in branches:
        assert event["intervention_kept"]["arrival_trace_hash"] == event["intervention_omitted"]["arrival_trace_hash"]
        assert event["intervention_kept"]["signal_samples"] == 100
