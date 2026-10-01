"""
test_flowsync_uq.py — Unit, Integration, and Stress Tests for FlowSync-UQ Method
=================================================================================
Milestone M2 Acceptance Criteria:
- Uncertainty is reproducible and correlates with observation degradation.
- Safety shield produces ZERO forbidden transitions in exhaustive randomized stress tests.
- Hysteresis prevents high-frequency fallback toggling.
- FlowSync-UQ operates deterministically and provides complete diagnostic traces.
"""
import numpy as np
import pytest

from server.app.controllers.safety_shield import SafetyShield, ShieldDecision
from server.app.controllers.supervisor import ControllerSupervisor, ControlAuthority
from server.app.controllers.flowsync_uq import FlowSyncUQController
from server.app.controllers.base import ControllerContext
from research.uncertainty.estimator import PerceptionUncertaintyEstimator, UncertaintyScore


def test_uncertainty_estimator_response():
    """Uncertainty score must be low on clean data and high on corrupted inputs."""
    estimator = PerceptionUncertaintyEstimator(threshold_high=0.45, threshold_low=0.25)
    estimator.reset()

    # 1. Clean observation with high detection confidence
    clean_queues = np.array([0.2] * 12, dtype=np.float32)
    score_clean = estimator.compute(
        observed_queues=clean_queues,
        forecast_features=np.array([0.2, 0.2, 0.2, 0.0, 0.0, 0.0, 0.0, 0.2]),
        detection_confidences=[0.95, 0.98, 0.92, 0.96],
        observation_age_ms=0.0,
        frame_dropped=False,
    )
    assert score_clean.score < 0.20
    assert not score_clean.is_unreliable

    # 2. Corrupted observation: low confidence + dropped frame + latency
    score_corrupt = estimator.compute(
        observed_queues=clean_queues * 0.1,  # sudden drop
        forecast_features=np.array([0.5, 0.5, 0.5, 0.0, 0.0, 0.0, 0.0, 0.5]),
        detection_confidences=[0.30, 0.35, 0.25],
        observation_age_ms=500.0,
        frame_dropped=True,
    )
    assert score_corrupt.score > 0.60
    assert score_corrupt.is_unreliable
    assert score_corrupt.features.missing_frame_penalty == 1.0


def test_safety_shield_minimum_green_enforcement():
    """Shield must block any phase switch attempted before 8.0s minimum green."""
    shield = SafetyShield(min_green_time=8.0)

    # Attempt to switch from phase 0 to phase 1 after only 4.0s green
    decision = shield.filter_action(
        proposed_action=1,
        current_phase=0,
        time_in_phase=4.0,
        color="GREEN",
    )
    assert decision.was_overridden is True
    assert decision.executed_action == 0  # Held in phase 0
    assert "minimum_green_guard" in str(decision.override_reason)

    # After 8.5s green, switch to phase 1 must be permitted
    decision_ok = shield.filter_action(
        proposed_action=1,
        current_phase=0,
        time_in_phase=8.5,
        color="GREEN",
    )
    assert decision_ok.was_overridden is False
    assert decision_ok.executed_action == 1


def test_safety_shield_max_green_enforcement():
    """Shield must force an alternative phase when max_green ceiling is reached."""
    shield = SafetyShield(max_green_time=40.0)

    # Attempt to hold phase 0 after 40.5s green
    decision = shield.filter_action(
        proposed_action=0,
        current_phase=0,
        time_in_phase=40.5,
        color="GREEN",
    )
    assert decision.was_overridden is True
    assert decision.executed_action != 0  # Diverted to alternative phase
    assert "max_green_ceiling" in str(decision.override_reason)


def test_safety_shield_anti_starvation_precedence():
    """Conflicting phase waiting >= 45s must override agent proposal."""
    shield = SafetyShield(starvation_threshold=45.0)

    # Phase 1 has waited 50.0s
    starvation_timers = {0: 0.0, 1: 50.0, 2: 10.0, 3: 5.0}

    decision = shield.filter_action(
        proposed_action=0,
        current_phase=0,
        time_in_phase=10.0,
        color="GREEN",
        starvation_timers=starvation_timers,
    )
    assert decision.was_overridden is True
    assert decision.executed_action == 1  # Forced service to starved phase 1
    assert "anti_starvation" in str(decision.override_reason)


def test_safety_shield_randomized_stress_test():
    """
    Exhaustive property-based stress test:
    Simulates 20,000 randomized steps feeding arbitrary adversarial/random proposals.
    Asserts ZERO illegal transitions occur:
    - Never switches during YELLOW or RED clearance.
    - Never switches before min_green_time.
    - Never exceeds max_green_time without switching.
    """
    shield = SafetyShield(min_green_time=8.0, max_green_time=40.0, yellow_duration=2.0, red_duration=3.0)
    rng = np.random.default_rng(42)

    current_phase = 0
    time_in_phase = 0.0
    color = "GREEN"
    pending_phase = None
    dt = 0.1

    forbidden_switches = 0
    premature_switches = 0
    max_green_violations = 0

    for step in range(20000):
        # Generate adversarial proposal (including out of bounds actions -1, 5)
        proposed_action = int(rng.choice([-1, 0, 1, 2, 3, 5, 99]))

        decision = shield.filter_action(
            proposed_action=proposed_action,
            current_phase=current_phase,
            time_in_phase=time_in_phase,
            color=color,
        )

        executed_action = decision.executed_action
        assert 0 <= executed_action <= 3, f"Action {executed_action} out of bounds!"

        # Invariant checks
        if color in ("YELLOW", "RED") and executed_action != current_phase:
            forbidden_switches += 1

        if color == "GREEN" and executed_action != current_phase:
            if time_in_phase < 8.0:
                premature_switches += 1
            # Initiate transition
            color = "YELLOW"
            pending_phase = executed_action
            time_in_phase = 0.0
            continue

        if color == "GREEN" and time_in_phase > 40.1:
            max_green_violations += 1

        # Advance physical time
        time_in_phase += dt
        if color == "YELLOW" and time_in_phase >= 2.0:
            color = "RED"
            time_in_phase = 0.0
        elif color == "RED" and time_in_phase >= 3.0:
            color = "GREEN"
            current_phase = pending_phase
            time_in_phase = 0.0

    assert forbidden_switches == 0
    assert premature_switches == 0
    assert max_green_violations == 0
    assert shield.total_evaluations == 20000


def test_supervisor_hysteresis_and_dwell_time():
    """Supervisor must enforce minimum dwell time and hysteretic return to prevent thrashing."""
    supervisor = ControllerSupervisor(
        threshold_high=0.45,
        threshold_low=0.25,
        min_dwell_steps=20,     # 2.0 seconds
        recovery_window_steps=5 # 0.5 seconds
    )
    supervisor.reset()

    # Step 0-5: Low uncertainty -> RL_ACTIVE
    for s in range(5):
        auth = supervisor.update(0.10, step=s)
        assert auth == ControlAuthority.RL_ACTIVE

    # Step 6: Surge above T_high -> switches to FALLBACK_ACTIVE
    auth = supervisor.update(0.50, step=6)
    assert auth == ControlAuthority.FALLBACK_ACTIVE

    # Step 7-15: Uncertainty drops to 0.15, but min_dwell (20 steps) NOT yet met -> remains FALLBACK
    for s in range(7, 16):
        auth = supervisor.update(0.15, step=s)
        assert auth == ControlAuthority.FALLBACK_ACTIVE, f"Switched prematurely at step {s}!"

    # Step 16-27: Dwell time satisfied (>= 20 steps) AND low uncertainty sustained for 5 steps -> returns to RL_ACTIVE
    for s in range(16, 28):
        auth = supervisor.update(0.15, step=s)

    assert auth == ControlAuthority.RL_ACTIVE
    assert supervisor.total_switches == 2


def test_flowsync_uq_controller_end_to_end():
    """FlowSyncUQController integrates all layers and produces complete diagnostics."""
    ctrl = FlowSyncUQController(threshold_high=0.45, threshold_low=0.25)
    ctrl.reset()
    obs = np.zeros(28, dtype=np.float32)

    # 1. Clean observation -> operates in D3QN RL mode
    ctx_clean = ControllerContext(
        timestep=1, dt=0.1, current_phase=0, time_in_phase=10.0, color="GREEN",
        can_switch_phase=True, valid_action_mask=np.array([True, True, False, False]),
        extra_telemetry={"observation_age_ms": 0.0, "frame_dropped": False}
    )
    action_clean = ctrl.act(obs, ctx_clean)
    diag_clean = ctrl.get_diagnostics()

    assert action_clean in [0, 1]
    assert diag_clean["authority"] == "rl_active"
    assert diag_clean["active_controller"] == "d3qn"
    assert "uncertainty_score" in diag_clean

    # 2. Highly degraded observation -> transfers to Max-Pressure fallback
    ctx_corrupt = ControllerContext(
        timestep=2, dt=0.1, current_phase=0, time_in_phase=10.0, color="GREEN",
        can_switch_phase=True, valid_action_mask=np.ones(4, dtype=bool),
        movement_queues={"north_straight": 0, "east_straight": 8, "west_straight": 5},
        extra_telemetry={"observation_age_ms": 800.0, "frame_dropped": True}
    )
    # Simulate high step change
    corrupted_obs = np.ones(28, dtype=np.float32) * 0.9
    action_fallback = ctrl.act(corrupted_obs, ctx_corrupt)
    diag_fallback = ctrl.get_diagnostics()

    assert diag_fallback["authority"] == "fallback_active"
    assert diag_fallback["active_controller"] == "max_pressure_fallback"
    assert diag_fallback["uncertainty_score"] > 0.45
