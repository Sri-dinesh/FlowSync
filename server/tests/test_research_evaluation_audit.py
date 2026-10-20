"""Regression tests for scientific validity of headless experiments."""
import copy

import numpy as np
import pytest
import torch

from research.experiments.engine import ExperimentRunner
from research.experiments.runtime import ObservedState, SignalAudit, apply_scenario_step
from research.noise.fault_injector import FaultProfile, PerceptionFaultInjector
from research.run_headless_evaluation import make_controller
from research.scenarios.scenario_schema import DemandProfile, ScenarioConfig
from server.app.controllers import D3QNController, FixedController, MaxPressureController
from server.app.controllers.base import ControllerContext
from server.app.controllers.safety_shield import SafetyShield
from server.app.simulation.environment import TrafficEnv
from server.app.simulation.spawner import TrafficProfile


@pytest.fixture
def checkpoint(tmp_path):
    # Test weights verify loading/provenance, not model quality.
    ctrl = D3QNController()
    path = tmp_path / "policy.pt"
    torch.save({"online_net": ctrl.agent.online_net.state_dict(), "episode": 17}, path)
    return str(path)


def scenario(steps=400):
    return ScenarioConfig("audit", "validation", "Audit", duration_steps=steps,
                          demand_profile=DemandProfile(base_lambda=1.2))


def test_untrained_policy_cannot_be_reported_as_evaluated():
    with pytest.raises(ValueError, match="explicit trained checkpoint"):
        ExperimentRunner().run(D3QNController(), scenario(), 42)


def test_all_ablations_share_the_exact_loaded_weights(checkpoint):
    names = ["d3qn", "flowsync_uq", "full_uq", "blind_d3qn", "without_shield",
             "without_fallback", "fixed_fallback"]
    hashes = set()
    for name in names:
        ctrl = make_controller(name, checkpoint)
        ctrl.reset(123)
        diag = ctrl.get_diagnostics()
        hashes.add(diag["checkpoint_hash"])
        assert diag["checkpoint_loaded"]
        assert diag["checkpoint_metadata"]["episode"] == 17
        policy = getattr(ctrl, "d3qn", ctrl)
        assert not policy.agent.online_net.training
    assert len(hashes) == 1


def test_missing_checkpoint_fails_and_never_uses_random_weights():
    with pytest.raises(FileNotFoundError):
        make_controller("d3qn", "/tmp/flowsync-nonexistent-checkpoint.pt")


def test_all_sensor_consumers_receive_corrupted_state():
    env = TrafficEnv(enable_watchdogs=False)
    env.reset(seed=42)
    env.intersection.inject_scenario({"east_straight": 10, "north_left": 5})
    env.intersection.signal.time_in_phase = 10
    clean = env._get_obs()
    injector = PerceptionFaultInjector(FaultProfile(miss_rate=1.0), seed=42)
    obs, ctx = ObservedState().build(env, clean, 0, injector)
    assert sum(ctx.movement_queues.values()) == 0
    assert ctx.valid_action_mask.tolist() == [True, False, False, False]
    assert obs[18] == 0  # Pressure must not leak the original queues.
    assert MaxPressureController().act(obs, ctx) == 0
    assert env.intersection.get_movement_queues()["east_straight"] == 10
    np.testing.assert_array_equal(clean, env._get_obs())


def test_vehicle_miss_rate_has_the_declared_mean_and_reset():
    injector = PerceptionFaultInjector(FaultProfile(miss_rate=0.3), seed=123)
    obs = np.zeros(28, dtype=np.float32)
    obs[:12] = np.tanh(10.0 / 15.0)
    for step in range(1000):
        injector.corrupt_observation(obs, step)
    assert injector.get_realized_diagnostics()["realized_miss_rate"] == pytest.approx(0.3, abs=0.01)
    injector.reset(123)
    assert injector.get_realized_diagnostics()["total_queries"] == 0


def test_camera_latency_and_drops_propagate_age_without_stale_lamps():
    env = TrafficEnv(enable_watchdogs=False)
    obs, _ = env.reset(seed=42)
    state = ObservedState()
    injector = PerceptionFaultInjector(FaultProfile(latency_ms=300), seed=42)
    for step in range(5):
        emitted, ctx = state.build(env, obs, step, injector)
    assert ctx.extra_telemetry["observation_age_ms"] == 300
    state = ObservedState()  # Independent fault episode: reset temporal history too.
    drops = PerceptionFaultInjector(FaultProfile(frame_drop_prob=1.0), seed=42)
    for step in range(15):
        emitted, ctx = state.build(env, obs, step, drops)
    assert ctx.extra_telemetry["frame_dropped"]
    assert ctx.extra_telemetry["observation_age_ms"] == 1400
    np.testing.assert_array_equal(emitted[12:18], obs[12:18])


def test_fallback_ablations_and_real_step_counters(checkpoint):
    ctx = ControllerContext(timestep=100, time_in_phase=10,
                            extra_telemetry={"observation_age_ms": 1200})
    obs = np.zeros(28, dtype=np.float32)
    full = make_controller("full_uq", checkpoint)
    fixed = make_controller("fixed_fallback", checkpoint)
    no_fb = make_controller("without_fallback", checkpoint)
    for ctrl in (full, fixed, no_fb):
        ctrl.act(obs, ctx)
    assert full.get_diagnostics()["active_controller"] == "max_pressure_fallback"
    assert fixed.get_diagnostics()["active_controller"] == "fixed_fallback"
    assert full.supervisor.total_fallback_steps == 1
    assert full.supervisor.total_rl_steps == 0
    assert no_fb.get_diagnostics()["active_controller"] == "d3qn"


def test_no_shield_actually_removes_controller_starvation_override(checkpoint):
    ctx = ControllerContext(timestep=100, time_in_phase=10,
                            phase_starvation_times={0: 0, 1: 60, 2: 0, 3: 0})
    obs = np.zeros(28, dtype=np.float32)
    full = make_controller("full_uq", checkpoint)
    no_shield = make_controller("without_shield", checkpoint)
    full.d3qn.act = no_shield.d3qn.act = lambda observation, context: 0
    assert full.act(obs, ctx) == 1
    assert no_shield.act(obs, ctx) == 0
    assert full.get_diagnostics()["was_overridden"]
    assert not no_shield.get_diagnostics()["was_overridden"]


def test_starvation_cannot_bypass_minimum_green():
    result = SafetyShield().filter_action(0, 0, 1.0, "GREEN", starvation_timers={1: 60})
    assert result.executed_action == 0


def test_bursts_are_directional_and_half_open():
    dp = DemandProfile(base_lambda=1.0, burst_events=[
        {"start_step": 0, "end_step": 5, "multiplier": 3, "directions": ["north", "south"]},
        {"start_step": 5, "end_step": 10, "multiplier": 3, "directions": ["east", "west"]},
    ])
    env = TrafficEnv()
    profile = TrafficProfile("p", "p", "")
    a = apply_scenario_step(env.intersection, profile, dp, 4)
    b = apply_scenario_step(env.intersection, profile, dp, 5)
    assert a["directional_weights"] == {"north": 3, "south": 3, "east": 1, "west": 1}
    assert b["directional_weights"] == {"north": 1, "south": 1, "east": 3, "west": 3}
    assert a["arrival_rate"] == b["arrival_rate"] == 2.0


def test_incident_changes_execution_without_changing_arrival_trace():
    clean = scenario(900)
    incident = copy.deepcopy(clean)
    incident.demand_profile.incident_events = [
        {"start_step": 0, "end_step": 900, "direction": "west", "capacity_factor": 0.0}
    ]
    runner = ExperimentRunner()
    a = runner.run(FixedController(), clean, 123, False)
    b = runner.run(FixedController(), incident, 123, False)
    assert a.arrival_trace_hash == b.arrival_trace_hash
    assert a.scenario_hash != b.scenario_hash
    assert b.total_vehicles_passed < a.total_vehicles_passed
    assert b.avg_delay > a.avg_delay
    assert b.scenario_diagnostics["incident_active_steps"] == 900


def test_per_direction_turn_ratios_reach_the_spawner():
    sc = scenario(400)
    sc.demand_profile.turn_ratios["east"] = {"straight": 0, "left": 1, "right": 0}
    result = ExperimentRunner().run(FixedController(), sc, 42, False)
    movements = result.scenario_diagnostics["generated_by_movement"]
    assert movements["east_left"] > 0
    assert movements["east_straight"] == movements["east_right"] == 0


def test_signal_monitor_detects_injected_faults():
    env = TrafficEnv()
    signal = env.intersection.signal
    audit = SignalAudit()
    signal.current_phase = 1
    audit.observe((0, "GREEN", 10), signal)
    assert audit.clearance_violations == 1
    signal.is_green_for = lambda direction, turn: True
    audit.observe((1, "GREEN", 10), signal)
    assert audit.conflicts == 1


def test_fixed_is_sensor_independent_and_audit_samples_are_present():
    runner = ExperimentRunner()
    sc = scenario()
    a = runner.run(FixedController(), sc, 42, False)
    b = runner.run(FixedController(), sc, 42, False,
                   PerceptionFaultInjector(FaultProfile(miss_rate=0.4), seed=999))
    assert (a.avg_delay, a.total_vehicles_passed) == (b.avg_delay, b.total_vehicles_passed)
    assert a.arrival_trace_hash == b.arrival_trace_hash
    assert b.observation_mae > 0
    assert a.safety_samples == sc.duration_steps
    assert a.executed_conflict_violations == a.executed_clearance_violations == 0


def test_result_bundle_refuses_to_overwrite_existing_evidence(tmp_path):
    result = ExperimentRunner().run(FixedController(), scenario(10), 42, False)
    result.save_bundle(tmp_path)
    with pytest.raises(FileExistsError):
        result.save_bundle(tmp_path)


def test_policy_keeps_trained_hold_interval(checkpoint):
    ctrl = make_controller("d3qn", checkpoint)
    obs = np.zeros(28, dtype=np.float32)
    ctx = ControllerContext(timestep=100, valid_action_mask=np.array([True, False, False, False]))
    assert ctrl.act(obs, ctx) == 0
    ctx.timestep = 101
    ctx.valid_action_mask = np.array([False, True, False, False])
    assert ctrl.act(obs, ctx) == 0
    ctx.timestep = 120
    assert ctrl.act(obs, ctx) == 1
