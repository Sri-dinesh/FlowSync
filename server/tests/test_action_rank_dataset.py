import copy

import pytest
import torch

from research.audit_policy_decisions import audit_run
from research.collect_action_rank_dataset import ROLES, plan_cells, selected_steps, verify_replay
from research.noise.fault_injector import FaultProfile
from research.scenarios.scenario_schema import ScenarioConfig
from server.app.rl.dqn_agent import DQNAgent


def test_plan_has_disjoint_roles_and_complete_cells():
    scenarios = {f"train_{i}": None for i in range(6)}
    plan = plan_cells(scenarios)
    assert len(plan) == 648
    assert len({(role, seed, parent, name, f.name) for role, seed, parent, name, f in plan}) == 648
    assert all(not set(ROLES[a]) & set(ROLES[b])
               for a in ROLES for b in ROLES if a != b)
    assert {role: sum(c[0] == role for c in plan) for role in ROLES} == {
        "fit": 216, "calibration": 360, "probe": 72}
    assert len(plan_cells({"train_low_balanced_01": None}, smoke=True)) == 1


def test_gate_sampling_ignores_outcomes_and_does_not_require_tick_200():
    source = dict(split="train", scenario="train_fixture", seed=95001,
                  fault=dict(name="clean"), events=[
                      dict(step=t, mask=[True, True, False, False], q_values=[0.] * 4)
                      for t in (0, 100, 800, 900)])
    assert selected_steps(source, 101, 1200) == [0, 100, 800]
    source["avg_delay"] = 9999
    source["events"][0]["q_values"] = [9999.] * 4
    assert selected_steps(source, 101, 1200) == [0, 100, 800]
    source["split"] = "test"
    with pytest.raises(ValueError, match="Training-only"):
        selected_steps(source, 101, 1200)


def test_sampling_is_deterministic_and_bounded():
    source = dict(split="train", scenario="train_fixture", seed=95001,
                  fault=dict(name="clean"), events=[
                      dict(step=t, mask=[True, True, True, True]) for t in range(0, 1200, 10)])
    steps = selected_steps(source, 101, 1200)
    assert len(steps) == len(set(steps)) == 3
    assert max(steps) <= 800
    assert steps == selected_steps(source, 101, 1200)
    source["events"].append(source["events"][0])
    with pytest.raises(ValueError, match="Duplicate"):
        selected_steps(source, 101, 1200)


@pytest.mark.parametrize("steps,all_actions", [([0, 0], True), ([-1], True), ([1000], True),
                                             ([1.5], True), ([0], False)])
def test_invalid_explicit_steps_fail_before_model_load(steps, all_actions):
    with pytest.raises(ValueError, match="Invalid explicit"):
        audit_run("not_needed.pt", ScenarioConfig("train_fixture", "train", "Fixture"),
                  95001, FaultProfile(), horizon=400, all_actions=all_actions, branch_steps=steps)


def test_explicit_steps_preserve_source_and_reject_missing_gate(tmp_path):
    torch.set_num_threads(1)
    torch.manual_seed(931)
    path = tmp_path / "parent.pt"
    agent = DQNAgent(36, "v7_36dim_observed")
    torch.save(agent.get_checkpoint_state(), path)
    sc = ScenarioConfig("train_fixture", "train", "Fixture")
    kwargs = dict(horizon=400, all_actions=True)
    source = audit_run(path, sc, 95001, FaultProfile(), max_events=0, **kwargs)
    steps = selected_steps(source, 101, 1200)
    branched = audit_run(path, sc, 95001, FaultProfile(), max_events=3, branch_steps=steps, **kwargs)
    verify_replay(source, branched, steps)
    altered = copy.deepcopy(branched)
    altered["avg_delay"] += .1
    with pytest.raises(ValueError, match="changed the source"):
        verify_replay(source, altered, steps)
    altered = copy.deepcopy(branched)
    event = next(e for e in altered["events"] if "all_action_branches" in e)
    event["all_action_branches"][0]["outcome"]["signal_samples"] = 0
    with pytest.raises(ValueError, match="branch signal"):
        verify_replay(source, altered, steps)
    # Tick 1 is not a policy decision gate.
    with pytest.raises(ValueError, match="not an eligible"):
        audit_run(path, sc, 95001, FaultProfile(), max_events=1, branch_steps=[1], **kwargs)
