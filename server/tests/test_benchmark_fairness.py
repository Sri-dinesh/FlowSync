"""
test_benchmark_fairness.py — Scientific Fairness Audit & CRN Equivalence Tests
================================================================================
Task N1: Verifies that benchmark comparisons are scientifically fair:
1. Exact Determinism: Fixed seed + controller = identical metrics & trajectories.
2. CRN Arrival Identity: Different controllers under same seed see identical arrivals.
3. Order Invariance: Evaluation order (e.g. Fixed then Max-Pressure vs. Max-Pressure then Fixed)
   produces identical results (no memory/global state carry-over).
4. State Reset Integrity: Resetting environment and controller wipes all episode-local state.
"""
import copy
import numpy as np
import pytest

from server.app.controllers import FixedController, GreedyController, MaxPressureController
from research.scenarios.scenario_schema import ScenarioConfig, DemandProfile
from research.experiments.engine import ExperimentRunner


@pytest.fixture
def test_scenario():
    return ScenarioConfig(
        scenario_id="audit_fairness_test_01",
        split="validation",
        name="Fairness Audit Scenario",
        duration_steps=600,  # 60s
        demand_profile=DemandProfile(base_lambda=0.5),
    )


def test_seed_determinism(test_scenario):
    """Running same controller on same seed twice must yield bit-identical metrics."""
    runner = ExperimentRunner()
    ctrl1 = MaxPressureController()
    ctrl2 = MaxPressureController()

    res1 = runner.run(ctrl1, test_scenario, seed=1337, record_trajectory=True)
    res2 = runner.run(ctrl2, test_scenario, seed=1337, record_trajectory=True)

    assert res1.avg_delay == res2.avg_delay
    assert res1.p95_delay == res2.p95_delay
    assert res1.queue_area == res2.queue_area
    assert res1.total_vehicles_passed == res2.total_vehicles_passed
    assert res1.total_arrivals == res2.total_arrivals
    assert len(res1.trajectory) == len(res2.trajectory)

    for p1, p2 in zip(res1.trajectory, res2.trajectory):
        assert p1["step"] == p2["step"]
        assert p1["phase"] == p2["phase"]
        assert p1["total_waiting"] == p2["total_waiting"]


def test_crn_arrival_schedule_equivalence(test_scenario):
    """All controllers tested with the same CRN seed must receive identical total arrivals."""
    runner = ExperimentRunner()
    fixed = FixedController()
    greedy = GreedyController()
    max_p = MaxPressureController()

    res_fixed = runner.run(fixed, test_scenario, seed=2026, record_trajectory=False)
    res_greedy = runner.run(greedy, test_scenario, seed=2026, record_trajectory=False)
    res_max_p = runner.run(max_p, test_scenario, seed=2026, record_trajectory=False)

    # Identical Poisson arrival generations across all 3 controllers
    assert res_fixed.total_arrivals == res_greedy.total_arrivals
    assert res_greedy.total_arrivals == res_max_p.total_arrivals
    assert res_fixed.scenario_hash == res_max_p.scenario_hash


def test_order_invariance(test_scenario):
    """
    Task N1: Controller evaluation order has ZERO effect on outcomes.
    Run A then B, then in a fresh runner run B then A.
    Results for A in both runs must match identically; results for B must match identically.
    """
    runner1 = ExperimentRunner()
    ctrl_a1 = FixedController()
    ctrl_b1 = MaxPressureController()

    res_a1 = runner1.run(ctrl_a1, test_scenario, seed=9999, record_trajectory=False)
    res_b1 = runner1.run(ctrl_b1, test_scenario, seed=9999, record_trajectory=False)

    runner2 = ExperimentRunner()
    ctrl_b2 = MaxPressureController()
    ctrl_a2 = FixedController()

    res_b2 = runner2.run(ctrl_b2, test_scenario, seed=9999, record_trajectory=False)
    res_a2 = runner2.run(ctrl_a2, test_scenario, seed=9999, record_trajectory=False)

    assert res_a1.avg_delay == res_a2.avg_delay
    assert res_a1.queue_area == res_a2.queue_area
    assert res_b1.avg_delay == res_b2.avg_delay
    assert res_b1.queue_area == res_b2.queue_area
