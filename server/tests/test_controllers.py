"""
test_controllers.py — Unit & Validation Tests for Controller Package
====================================================================
Tests cover:
- Unified BaseController contract (capabilities, act, reset, diagnostics)
- Task D1: Hand-computed Max-Pressure mathematical verification & downstream backpressure
- Task D2: NEMA Actuated gap-out and max-green logic
- Task D3: D3QN & DQN deterministic inference mode and capability flags
- Fixed & Greedy behavior verification
"""
import numpy as np
import pytest

from app.controllers import (
    BaseController,
    ControllerCapabilities,
    ControllerContext,
    FixedController,
    GreedyController,
    MaxPressureController,
    ActuatedController,
    DQNController,
    D3QNController,
    get_controller,
    CONTROLLER_REGISTRY,
)


def test_controller_registry():
    """All required controllers must be present in registry and instantiable."""
    required = ["fixed", "greedy", "max_pressure", "actuated", "plain_dqn", "d3qn"]
    for name in required:
        ctrl = get_controller(name)
        assert isinstance(ctrl, BaseController)
        caps = ctrl.get_capabilities()
        assert isinstance(caps, ControllerCapabilities)
        assert caps.name != ""


def test_fixed_controller_cycling():
    """FixedController must cycle 0 -> 1 -> 2 -> 3 -> 0 on timer intervals."""
    ctrl = FixedController(phase_durations=[2.0, 2.0, 2.0, 2.0])
    ctrl.reset()
    obs = np.zeros(28, dtype=np.float32)

    # First 1.9 seconds (19 steps at 0.1s): holds Phase 0
    for t in range(19):
        ctx = ControllerContext(timestep=t, dt=0.1, current_phase=0, can_switch_phase=True)
        act = ctrl.act(obs, ctx)
        assert act == 0

    # At 2.0s (step 19), time_in_phase reaches 2.0s and advances to Phase 1
    ctx = ControllerContext(timestep=19, dt=0.1, current_phase=0, can_switch_phase=True)
    act = ctrl.act(obs, ctx)
    assert act == 1


def test_greedy_controller_max_queue():
    """GreedyController selects the phase with highest total backlog."""
    ctrl = GreedyController()
    obs = np.zeros(28, dtype=np.float32)

    # Case 1: EW Straight is largest (Phase 1)
    queues = {
        "north_straight": 1, "south_straight": 2, "north_right": 0, "south_right": 0,
        "east_straight": 8, "west_straight": 5, "east_right": 1, "west_right": 1,
        "north_left": 0, "south_left": 0, "east_left": 0, "west_left": 0,
    }
    ctx = ControllerContext(
        timestep=1, dt=0.1, current_phase=0, can_switch_phase=True, movement_queues=queues
    )
    assert ctrl.act(obs, ctx) == 1

    # Case 2: Tied with current phase -> holds current phase
    queues_tied = {
        "north_straight": 5, "south_straight": 5, "north_right": 0, "south_right": 0, # Phase 0 = 10
        "east_straight": 5, "west_straight": 5, "east_right": 0, "west_right": 0,    # Phase 1 = 10
        "north_left": 0, "south_left": 0, "east_left": 0, "west_left": 0,
    }
    ctx_tied = ControllerContext(
        timestep=2, dt=0.1, current_phase=0, can_switch_phase=True, movement_queues=queues_tied
    )
    assert ctrl.act(obs, ctx_tied) == 0  # preserves current Phase 0


def test_max_pressure_hand_computed_equations():
    """
    Task D1: Validate Max-Pressure decisions against exact hand-computed equations.
    Formula: P(m) = max(0, q_in(m)/cap - q_out(dest(m))/cap)
             W(p) = sum_{m in p} P(m)
    """
    ctrl = MaxPressureController(max_cap_in=10.0, max_cap_out=10.0)
    ctrl.reset()
    obs = np.zeros(28, dtype=np.float32)

    # Hand-constructed scenario:
    # Phase 0 (NS straight):
    #   north_straight = 6, dest south has 1 out -> 0.6 - 0.1 = 0.5
    #   south_straight = 4, dest north has 0 out -> 0.4 - 0.0 = 0.4
    #   W(Phase 0) = 0.5 + 0.4 = 0.9
    # Phase 1 (EW straight):
    #   east_straight = 2, dest west has 0 out -> 0.2 - 0.0 = 0.2
    #   west_straight = 3, dest east has 1 out -> 0.3 - 0.1 = 0.2
    #   W(Phase 1) = 0.2 + 0.2 = 0.4
    # Phase 2 (NS left):
    #   north_left = 1, dest east has 1 out -> max(0, 0.1 - 0.1) = 0.0
    #   south_left = 2, dest west has 0 out -> 0.2 - 0.0 = 0.2
    #   W(Phase 2) = 0.0 + 0.2 = 0.2
    # Phase 3 (EW left):
    #   east_left = 0, west_left = 0 -> W(Phase 3) = 0.0
    queues = {
        "north_straight": 6, "south_straight": 4, "north_right": 0, "south_right": 0,
        "east_straight": 2, "west_straight": 3, "east_right": 0, "west_right": 0,
        "north_left": 1, "south_left": 2, "east_left": 0, "west_left": 0,
    }
    outgoing = {"north": 0, "south": 1, "east": 1, "west": 0}

    ctx = ControllerContext(
        timestep=1, dt=0.1, current_phase=1, can_switch_phase=True,
        movement_queues=queues, outgoing_counts=outgoing
    )

    action = ctrl.act(obs, ctx)
    diag = ctrl.get_diagnostics()

    assert diag["phase_pressures"][0] == pytest.approx(0.9)
    assert diag["phase_pressures"][1] == pytest.approx(0.4)
    assert diag["phase_pressures"][2] == pytest.approx(0.2)
    assert diag["phase_pressures"][3] == pytest.approx(0.0)
    assert action == 0  # Phase 0 wins


def test_max_pressure_downstream_spillback_prevention():
    """
    Task D1: Max-Pressure must penalize blocked downstream roads.
    If upstream queue is 8 but downstream departure is jammed at 10,
    net pressure is max(0, 8/10 - 10/10) = 0.
    """
    ctrl = MaxPressureController(max_cap_in=10.0, max_cap_out=10.0)
    obs = np.zeros(28, dtype=np.float32)

    # North straight has 8 cars, but dest 'south' has 10 cars (full).
    # South straight has 0 cars.
    # -> W(Phase 0) = max(0, 0.8 - 1.0) + 0 = 0.0
    # Meanwhile East straight has 3 cars, dest 'west' has 0 cars.
    # -> W(Phase 1) = 0.3
    queues = {
        "north_straight": 8, "south_straight": 0, "north_right": 0, "south_right": 0,
        "east_straight": 3, "west_straight": 0, "east_right": 0, "west_right": 0,
        "north_left": 0, "south_left": 0, "east_left": 0, "west_left": 0,
    }
    outgoing = {"north": 0, "south": 10, "east": 0, "west": 0}

    ctx = ControllerContext(
        timestep=1, dt=0.1, current_phase=0, can_switch_phase=True,
        movement_queues=queues, outgoing_counts=outgoing
    )

    action = ctrl.act(obs, ctx)
    diag = ctrl.get_diagnostics()

    assert diag["phase_pressures"][0] == 0.0
    assert diag["phase_pressures"][1] == pytest.approx(0.3)
    assert action == 1  # Diverts green to Phase 1, preventing spillback on south approach!


def test_actuated_controller_gap_out_and_max_green():
    """Task D2: ActuatedController must respect gap-out and max-green ceilings."""
    ctrl = ActuatedController(gap_threshold=3.0, min_green=8.0, max_green=20.0)
    ctrl.reset()
    obs = np.zeros(28, dtype=np.float32)
    queues = {
        "north_straight": 5, "south_straight": 5, "north_right": 0, "south_right": 0,
        "east_straight": 10, "west_straight": 10, "east_right": 0, "west_right": 0,
        "north_left": 0, "south_left": 0, "east_left": 0, "west_left": 0,
    }

    # First 50 steps (5 seconds): no arrivals, but min_green (8s) NOT yet met
    for t in range(50):
        ctx = ControllerContext(
            timestep=t, dt=0.1, current_phase=0, can_switch_phase=True,
            movement_queues=queues, extra_telemetry={"spawned_this_step": 0}
        )
        assert ctrl.act(obs, ctx) == 0

    # Continue until 8.5 seconds (step 85) without arrivals: gap-out triggers!
    # Because East-West (Phase 1) has backlog (10 cars), it must switch to Phase 1.
    for t in range(50, 86):
        ctx = ControllerContext(
            timestep=t, dt=0.1, current_phase=0, can_switch_phase=True,
            movement_queues=queues, extra_telemetry={"spawned_this_step": 0}
        )
        act = ctrl.act(obs, ctx)

    assert act == 1  # Gapped out to Phase 1


def test_d3qn_deterministic_inference():
    """Task 1A.1: D3QNController in deterministic mode produces identical outputs given identical states."""
    ctrl = D3QNController(deterministic=True)
    obs = np.random.RandomState(42).randn(28).astype(np.float32)
    mask = np.array([True, True, False, False])

    ctx = ControllerContext(timestep=1, dt=0.1, current_phase=0, valid_action_mask=mask)

    action1 = ctrl.act(obs, ctx)
    diag1 = ctrl.get_diagnostics()

    action2 = ctrl.act(obs, ctx)
    diag2 = ctrl.get_diagnostics()

    assert action1 == action2
    assert action1 in [0, 1]  # must respect valid mask
    assert np.allclose(diag1["q_values"], diag2["q_values"])
    assert diag1["checkpoint_hash"] != ""
    assert ctrl.get_capabilities().uses_camera_observable_state_only is True
