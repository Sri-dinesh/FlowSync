import copy
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from research.audit_policy_decisions import alternative_branch, audit_run
from research.experiments.engine import ExperimentRunner
from research.noise.fault_injector import FaultProfile, PerceptionFaultInjector
from research.scenarios.scenario_schema import ScenarioConfig
from server.app.controllers.base import ControllerContext
from server.app.controllers.flowsync_uq import FlowSyncUQController
from server.app.controllers.safety_shield import SafetyShield
from server.app.rl.dqn_agent import DQNAgent


def test_alternative_changes_hold_not_next_decision_time():
    policy = SimpleNamespace(_held_action=0, _next_decision_step=120)
    controller = SimpleNamespace(d3qn=policy, safety_shield=SafetyShield())
    original = (None, None, None, controller)
    context = ControllerContext(100, time_in_phase=10., valid_action_mask=np.ones(4, dtype=bool))
    state, action = alternative_branch(copy.deepcopy(original), 1, context)
    assert action == state[3].d3qn._held_action == 1
    assert state[3].d3qn._next_decision_step == 120
    assert original[3].d3qn._held_action == 0


@pytest.mark.parametrize("split", ["validation", "test"])
def test_audit_refuses_nontraining_split(split):
    with pytest.raises(ValueError, match="training scenarios"):
        audit_run("not_needed.pt", ScenarioConfig("other", split, "Other"), 1, FaultProfile())


@pytest.mark.parametrize("fault", [FaultProfile(), FaultProfile(miss_rate=.2, latency_ms=200)])
def test_auditor_preserves_source_policy_trajectory(tmp_path, fault):
    torch.set_num_threads(1)
    path = tmp_path/"policy.pt"
    agent = DQNAgent()
    with torch.no_grad():
        for parameter in agent.online_net.parameters():
            parameter.zero_()
        agent.online_net.advantage_stream[-1].bias[0] = 1.
    torch.save(agent.get_checkpoint_state(), path)
    scenario = ScenarioConfig("train_fixture", "train", "Fixture", duration_steps=1200)
    measured = audit_run(path, scenario, 92001, fault)
    regular = ExperimentRunner().run(FlowSyncUQController(checkpoint_path=str(path), enable_fallback=False),
        scenario, 92001, record_trajectory=False, fault_injector=PerceptionFaultInjector(fault, seed=182001))
    assert round(measured["avg_delay"], 3) == regular.avg_delay
    assert measured["arrival_trace_hash"] == regular.arrival_trace_hash
    events = [e for e in measured["events"] if "policy_branch" in e]
    assert events
    for event in events:
        kept, alternative = event["policy_branch"], event["teacher_branch"]
        assert kept["arrival_trace_hash"] == alternative["arrival_trace_hash"]
        for branch in (kept, alternative):
            assert branch["signal_samples"] == 200
            assert branch["signal_violations"] == 0
            assert sum(branch["reward_components"].values()) == pytest.approx(branch["undiscounted_training_reward"])
