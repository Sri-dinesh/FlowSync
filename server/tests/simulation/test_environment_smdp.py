import numpy as np
import pytest

from app.simulation.environment import TrafficEnv


def test_rejected_min_green_request_is_not_labeled_executed():
    env = TrafficEnv(max_steps=100)
    env.reset(seed=4)

    _, _, _, _, info = env.step(3)

    assert info["proposed_action"] == 3
    assert info["executed_action"] == 0
    assert env.intersection.signal.current_phase == 0


def test_decision_transition_reaches_next_executable_gate():
    env = TrafficEnv(max_steps=500)
    state, reset_info = env.reset_to_decision(seed=7)
    mask = reset_info["valid_action_mask"]
    action = int(np.flatnonzero(mask)[0])

    next_state, _, terminated, truncated, info = env.step_decision(action)

    assert state.shape == next_state.shape == (28,)
    assert not terminated
    assert not truncated
    assert info["decision_duration_seconds"] >= 2.0
    assert 0.0 < info["bootstrap_discount"] < 1.0
    assert env.intersection.signal.can_switch_phase


def test_environment_seed_controls_arrival_trace():
    def trace(seed):
        env = TrafficEnv(max_steps=300)
        env.reset(seed=seed)
        values = []
        for _ in range(300):
            env.step(0)
            values.append(env.intersection._generated_last_tick)
        return values

    assert trace(123) == trace(123)
    assert trace(123) != trace(124)


def test_configured_horizon_is_respected():
    env = TrafficEnv(max_steps=700)
    env.reset(seed=9)
    truncated = False
    for _ in range(700):
        _, _, _, truncated, _ = env.step(0)
    assert truncated
    assert env.intersection.timestep == 700


def test_v5_charges_one_switch_once_without_changing_traffic_dynamics():
    def trace(version):
        env = TrafficEnv(max_steps=500, enable_watchdogs=False, reward_version=version)
        env.reset_to_decision(seed=7)
        target = (env.intersection.signal.current_phase + 1) % 4
        costs, physical = [], []
        for tick in range(140):
            _, _, _, _, info = env.step(target)
            cost = info["reward_components"]["switch"]
            if cost:
                costs.append((tick, cost))
            signal = env.intersection.signal
            physical.append((signal.current_phase, signal.color, signal.time_in_phase,
                             env.intersection.total_passed, env.intersection.get_avg_wait_time()))
            assert info["reward_version"] == version
        return costs, physical

    legacy, old_traffic = trace("v4_incremental_delay")
    corrected, new_traffic = trace("v5_single_switch_delay")
    assert len(legacy) == 3  # Preserve and document the historical bug explicitly.
    assert len(corrected) == 1 and corrected[0][0] == 0
    assert corrected[0][1] == legacy[0][1]
    assert old_traffic == new_traffic


def test_v5_does_not_penalize_rejected_requests():
    env = TrafficEnv(max_steps=100, enable_watchdogs=False, reward_version="v5_single_switch_delay")
    env.reset(seed=4)
    for _ in range(70):
        _, _, _, _, info = env.step(1)
        assert info["reward_components"]["switch"] == 0
    with pytest.raises(ValueError, match="Unsupported reward version"):
        TrafficEnv(reward_version="unknown")
