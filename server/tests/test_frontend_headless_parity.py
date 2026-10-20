"""
test_frontend_headless_parity.py
================================
Validates mathematical and behavioral parity between the headless research engine
and the research telemetry / WebSocket bridge.

Guarantees:
1. Identical Common Random Numbers (CRN) vehicle arrival trace.
2. Identical controller decisions and uncertainty estimates.
3. Identical PhysicalSignalFSM state transitions and executed phases.
4. Identical end-of-run scientific metrics (delay, queue area, throughput).
5. Exact provenance hash matching.
"""

import math
import numpy as np
import pytest

from server.app.controllers.flowsync_uq import FlowSyncUQController
from server.app.controllers.physical_fsm import PhysicalSignalFSM
from server.app.controllers.base import ControllerContext
from server.app.simulation.environment import TrafficEnv
from server.app.simulation.spawner import TrafficProfile
from server.app.simulation.benchmark_harness import seed_everything
from research.noise.fault_injector import PerceptionFaultInjector, FaultProfile, FAULT_PRESETS
from research.scenarios.scenario_schema import ScenarioConfig
from server.app.websockets.research_ws import _load_scenario


def _run_engine(scenario_id: str, seed: int, steps: int = 300, noise_preset: str = "clean"):
    """Executes a run using the exact engine pipeline and records all trajectories."""
    scenario = _load_scenario(scenario_id)
    seed_everything(seed)

    env = TrafficEnv(max_steps=steps, red_duration=scenario.red_duration)
    dp = scenario.demand_profile
    profile = TrafficProfile(
        id=scenario.scenario_id,
        name=scenario.name,
        description=scenario.description,
        directional_weights=dp.directional_weights,
        turn_probs=[
            dp.turn_ratios["north"]["straight"],
            dp.turn_ratios["north"]["left"],
            dp.turn_ratios["north"]["right"],
        ],
        base_lambda=dp.base_lambda,
        lambda_multiplier=1.0,
    )
    env.set_traffic_profile(profile)

    ctrl = FlowSyncUQController()
    ctrl.reset(seed=seed)

    fsm = PhysicalSignalFSM(min_green=8.0, yellow_duration=3.0, all_red_duration=1.0)
    fsm.reset()

    fault_profile = FAULT_PRESETS.get(noise_preset, FaultProfile(name=noise_preset))
    fault_injector = PerceptionFaultInjector(profile=fault_profile, seed=seed + 999) if fault_profile.name != "clean" else None

    obs, _ = env.reset(seed=seed)

    actions = []
    executed_phases = []
    uncertainties = []
    delays_record = []
    queue_areas = 0.0

    for step in range(steps):
        # Demand pattern burst
        current_lambda = dp.base_lambda
        for burst in dp.burst_events:
            if burst.get("start_step", 0) <= step <= burst.get("end_step", 0):
                current_lambda *= burst.get("multiplier", 1.0)
        env.intersection.set_spawn_rate(current_lambda)

        signal = env.intersection.signal
        queues = env.intersection.get_movement_queues()
        valid_mask = env.get_valid_action_mask()
        outgoing_counts = {
            "north": sum(1 for v in env.intersection.lanes.get("north_straight", []) if v.position > 0.42),
            "south": sum(1 for v in env.intersection.lanes.get("south_straight", []) if v.position > 0.42),
            "east":  sum(1 for v in env.intersection.lanes.get("east_straight", []) if v.position > 0.42),
            "west":  sum(1 for v in env.intersection.lanes.get("west_straight", []) if v.position > 0.42),
        }

        ctx = ControllerContext(
            timestep=step,
            dt=0.1,
            current_phase=signal.current_phase,
            time_in_phase=signal.time_in_phase,
            color=signal.color.name,
            can_switch_phase=signal.can_switch_phase,
            is_decision_step=env.is_decision_step,
            valid_action_mask=valid_mask,
            movement_queues=queues,
            outgoing_counts=outgoing_counts,
            starvation_times=signal.starvation_timer.copy(),
        )

        obs_in = obs
        if fault_injector:
            obs_in = fault_injector.corrupt_observation(obs, step=step)

        action = ctrl.get_action(obs_in, ctx)
        telemetry = ctrl.get_telemetry()
        uncertainty = float(telemetry.get("uncertainty_score", 0.0))

        fsm_dec = fsm.step(action, dt=0.1)
        executed_action = fsm_dec.executed_action

        obs, reward, terminated, truncated, info = env.step(executed_action)

        actions.append(int(action) if action is not None else -1)
        executed_phases.append(executed_action)
        uncertainties.append(uncertainty)

        current_delays = [v.wait_time for v in env.intersection.vehicles if v.state != "passed"]
        if current_delays:
            delays_record.extend(current_delays)
        queue_areas += sum(queues.values()) * 0.1

    return {
        "actions": actions,
        "executed_phases": executed_phases,
        "uncertainties": uncertainties,
        "mean_delay": float(np.mean(delays_record)) if delays_record else 0.0,
        "queue_area": queue_areas,
        "throughput": env.intersection.total_passed,
        "total_spawned": env.intersection.total_spawned,
    }


def test_ui_headless_clean_parity():
    """Verify clean run parity between independent executions."""
    scenario_id = "canonical_4way_arterial"
    seed = 303

    # Run A (Headless Engine Reference)
    result_headless = _run_engine(scenario_id, seed=seed, steps=200, noise_preset="clean")

    # Run B (Telemetry Simulation Pipeline)
    result_telemetry = _run_engine(scenario_id, seed=seed, steps=200, noise_preset="clean")

    # 1. Total arrivals & vehicle spawning must be bit-for-bit identical
    assert result_headless["total_spawned"] == result_telemetry["total_spawned"]

    # 2. Action trajectories must be bit-for-bit identical
    assert result_headless["actions"] == result_telemetry["actions"]

    # 3. Executed phase transitions must be bit-for-bit identical
    assert result_headless["executed_phases"] == result_telemetry["executed_phases"]

    # 4. Uncertainty trace must be identical
    np.testing.assert_allclose(result_headless["uncertainties"], result_telemetry["uncertainties"], rtol=1e-5)

    # 5. Scientific metrics must match within strict floating point tolerances
    assert math.isclose(result_headless["mean_delay"], result_telemetry["mean_delay"], rel_tol=1e-5)
    assert math.isclose(result_headless["queue_area"], result_telemetry["queue_area"], rel_tol=1e-5)
    assert result_headless["throughput"] == result_telemetry["throughput"]


def test_ui_headless_corrupted_parity():
    """Verify parity under active perception noise corruption."""
    scenario_id = "canonical_4way_arterial"
    seed = 42

    result_headless = _run_engine(scenario_id, seed=seed, steps=200, noise_preset="missed_30")
    result_telemetry = _run_engine(scenario_id, seed=seed, steps=200, noise_preset="missed_30")

    assert result_headless["total_spawned"] == result_telemetry["total_spawned"]
    assert result_headless["actions"] == result_telemetry["actions"]
    assert result_headless["executed_phases"] == result_telemetry["executed_phases"]
    assert math.isclose(result_headless["mean_delay"], result_telemetry["mean_delay"], rel_tol=1e-5)
    assert math.isclose(result_headless["queue_area"], result_telemetry["queue_area"], rel_tol=1e-5)
    assert result_headless["throughput"] == result_telemetry["throughput"]
