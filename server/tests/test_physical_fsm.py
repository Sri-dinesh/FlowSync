"""
test_physical_fsm.py — Tests for Mandatory Physical Signal State Machine
========================================================================
Validates that:
1. PhysicalSignalFSM enforces minimum green time.
2. Mandatory yellow (3s) and all-red (1s) clearance intervals are preserved.
3. Illegal proposals (early switch, clearance override) are recorded as proposed violations.
4. Executed clearance violations are identically ZERO under all proposals.
5. Randomized stress proposals produce 0 executed violations.
"""
import random
import pytest
from server.app.controllers.physical_fsm import PhysicalSignalFSM, FSMColor


def test_physical_fsm_initial_state():
    fsm = PhysicalSignalFSM(min_green=8.0, yellow_duration=3.0, all_red_duration=1.0)
    assert fsm.current_phase == 0
    assert fsm.color == FSMColor.GREEN
    assert fsm.total_proposed_violations == 0
    assert fsm.total_executed_violations == 0


def test_physical_fsm_min_green_enforcement():
    fsm = PhysicalSignalFSM(min_green=8.0, yellow_duration=3.0, all_red_duration=1.0)

    # Step at t=0 proposing switch from 0 to 1
    d1 = fsm.step(proposed_phase=1, dt=1.0)
    assert d1.is_proposed_violation is True
    assert "premature_switch" in d1.violation_reason
    assert d1.executed_phase == 0
    assert d1.executed_violation is False
    assert fsm.color == FSMColor.GREEN

    # Step for 7 more seconds
    for _ in range(7):
        d = fsm.step(proposed_phase=1, dt=1.0)
        assert d.executed_violation is False

    # Now time_in_phase >= 8.0s, switch should be accepted and enter YELLOW
    d_switch = fsm.step(proposed_phase=1, dt=1.0)
    assert d_switch.is_proposed_violation is False
    assert fsm.color == FSMColor.YELLOW
    assert fsm.pending_phase == 1


def test_physical_fsm_mandatory_clearance_progression():
    fsm = PhysicalSignalFSM(min_green=8.0, yellow_duration=3.0, all_red_duration=1.0)

    # Advance through min green
    for _ in range(8):
        fsm.step(proposed_phase=0, dt=1.0)

    # Initiate switch to phase 2
    d_init = fsm.step(proposed_phase=2, dt=1.0)
    assert d_init.is_proposed_violation is False
    assert fsm.color == FSMColor.YELLOW

    # Yellow clearance lasts 3s (dt=1.0 per step)
    fsm.step(proposed_phase=2, dt=1.0)  # yellow t=1.0 -> 2.0
    fsm.step(proposed_phase=2, dt=1.0)  # yellow t=2.0 -> 3.0 -> transitions to RED
    assert fsm.color == FSMColor.RED

    # All-red clearance lasts 1s -> transitions to GREEN on phase 2
    fsm.step(proposed_phase=2, dt=1.0)
    assert fsm.color == FSMColor.GREEN
    assert fsm.current_phase == 2


def test_physical_fsm_randomized_adversarial_stress():
    """Subject the physical FSM to 10,000 random adversarial phase requests."""
    fsm = PhysicalSignalFSM(min_green=8.0, yellow_duration=3.0, all_red_duration=1.0)
    rng = random.Random(42)

    for _ in range(10000):
        action = rng.choice([0, 1, 2, 3])
        dt = rng.choice([0.5, 1.0, 1.5])
        decision = fsm.step(proposed_phase=action, dt=dt)
        # Executed violation must NEVER happen under any circumstances
        assert decision.executed_violation is False

    # Ensure proposed violations were caught and logged
    assert fsm.total_proposed_violations > 0
    assert fsm.total_executed_violations == 0
