"""Matched controller interventions and complete crossed evaluation reporting."""
import numpy as np
import pytest
import torch

from research import evaluate_replicates as evaluator
from research.experiments.engine import ExperimentRunner
from research.experiments.shielded_controller import ShieldedController
from research.noise.fault_injector import FaultProfile, PerceptionFaultInjector
from research.scenarios.scenario_schema import ScenarioConfig
from server.app.controllers.base import ControllerContext
from server.app.controllers.d3qn import D3QNController
from server.app.controllers.flowsync_uq import FlowSyncUQController
from server.app.controllers.max_pressure import MaxPressureController
from server.app.rl.dqn_agent import DQNAgent


def test_max_pressure_shield_intervention_and_reset():
    ctrl = ShieldedController(MaxPressureController())
    context = ControllerContext(timestep=100, current_phase=0, time_in_phase=10.,
                                movement_queues={"north_straight": 9, "east_left": 1},
                                valid_action_mask=np.ones(4, dtype=bool),
                                phase_starvation_times={0: 0., 1: 0., 2: 0., 3: 50.})
    assert ctrl.controller.act(np.zeros(28), context) == 0
    assert ctrl.act(np.zeros(28), context) == 3
    diag = ctrl.get_diagnostics()
    assert diag["was_overridden"]
    assert diag["shield"]["total_overrides"] == 1
    assert not diag["fallback_enabled"]
    assert ctrl.get_capabilities().to_dict()["supports_safety_shield"]
    ctrl.reset(42)
    assert ctrl.get_diagnostics()["shield"]["total_overrides"] == 0


@pytest.mark.parametrize("fault", [FaultProfile(), FaultProfile(miss_rate=.3, latency_ms=1000)])
def test_generic_shield_matches_uq_shield_adapter(tmp_path, fault):
    torch.set_num_threads(1)
    path = tmp_path / "fixture.pt"
    torch.save(DQNAgent().get_checkpoint_state(), path)
    scenario = ScenarioConfig("val_matched_shield", "validation", "Matched", duration_steps=1000)
    controllers = [ShieldedController(D3QNController(checkpoint_path=str(path))),
                   FlowSyncUQController(checkpoint_path=str(path), enable_fallback=False)]
    results = [ExperimentRunner().run(ctrl, scenario, 21001, record_trajectory=False,
               fault_injector=PerceptionFaultInjector(fault, seed=111001)) for ctrl in controllers]
    for field in ("avg_delay", "p95_delay", "total_vehicles_passed", "queue_area", "starvation_count",
                  "arrival_trace_hash", "checkpoint_hash", "shield_interventions", "safety_samples"):
        assert getattr(results[0], field) == getattr(results[1], field)
    assert all(r.fallback_steps == 0 for r in results)


def fixture_rows():
    rows = []
    for traffic in (81001, 81002):
        labels = [(name, None) for name in ("fixed", "actuated", "greedy", "max_pressure", "max_pressure_shield")]
        labels += [(f"{name}_seed{seed}", seed) for name in ("d3qn", "d3qn_shield", "flowsync_uq") for seed in (101, 202, 303)]
        for label, train in labels:
            delay = 8 if label.startswith("d3qn_shield") else 10
            rows.append({"label": label, "training_seed": train, "scenario_id": "test_fixture",
                         "condition": "clean", "seed": traffic, "avg_delay": delay, "p95_delay": 2*delay,
                         "starvation_count": 0, "fallback_steps": 0, "shield_interventions": 0,
                         "executed_conflict_violations": 0, "executed_clearance_violations": 0,
                         "safety_samples": 100, "num_steps": 100, "total_vehicles_passed": 30,
                         "arrival_trace_hash": str(traffic)})
    return rows


@pytest.fixture
def fast_bootstrap(monkeypatch):
    original = evaluator.crossed_bootstrap
    monkeypatch.setattr(evaluator, "crossed_bootstrap", lambda data: original(data, draws=20))


def test_matched_comparisons_include_paired_component_effects_and_tails(fast_bootstrap):
    report = evaluator.summarize(fixture_rows(), matched_shield=True)
    stats = report["comparisons"]
    assert stats["d3qn_shield_vs_max_pressure_shield_avg_delay"]["mean_delay_saved_s"] == 2
    assert stats["d3qn_shield_vs_max_pressure_shield_p95_delay"]["mean_delay_saved_s"] == 4
    assert stats["flowsync_uq_vs_d3qn_shield_avg_delay"]["mean_delay_saved_s"] == -2
    assert stats["max_pressure_shield_vs_max_pressure_avg_delay"]["mean_delay_saved_s"] == 0
    assert not report["publication_ready"]


@pytest.mark.parametrize("defect", ["duplicate", "missing", "arrivals", "safety"])
def test_incomplete_or_unpaired_reports_fail_closed(fast_bootstrap, defect):
    rows = fixture_rows()
    if defect == "duplicate":
        rows.append(rows[0])
    elif defect == "missing":
        rows.pop()
    elif defect == "arrivals":
        rows[0]["arrival_trace_hash"] = "different"
    else:
        rows[0]["safety_samples"] = 99
    with pytest.raises(ValueError):
        evaluator.summarize(rows, matched_shield=True)
