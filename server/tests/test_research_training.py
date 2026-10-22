"""Research training must use evaluation dynamics and never select on test data."""
import random
import json
from types import SimpleNamespace
import numpy as np
import pytest
import torch

from research.training.train_policy import BudgetExceeded, RunBudget, collect_episode, load_split, preserve_rng, training_scenario
from research.training import train_policy
from research.evaluation.select_shield_control import candidate_labels
from research.noise.fault_injector import FaultProfile
from research.experiments.engine import ExperimentRunner
from research.scenarios.scenario_schema import ScenarioConfig
from server.app.controllers.d3qn import D3QNController
from server.app.controllers.flowsync_uq import FlowSyncUQController
from server.app.rl.dqn_agent import DQNAgent
from server.app.rl.observations import OBSERVED_VERSION, encode_policy_observation
from server.app.controllers.base import ControllerContext


def test_collection_matches_evaluation_without_learning():
    torch.manual_seed(41)
    agent = DQNAgent()
    sc = ScenarioConfig("training_parity", "train", "Parity", duration_steps=500)
    collected = collect_episode(agent, sc, 32001, FaultProfile(), epsilon=0, learn=False)
    result = ExperimentRunner().run(D3QNController(agent=agent), sc, 32001,
                                    record_trajectory=False, allow_untrained=True)
    assert collected["avg_delay"] == pytest.approx(result.avg_delay, abs=.001)
    assert collected["decisions"] > 0
    assert all(t[4] == 0 for t in agent.replay_buffer.tree.data if t is not None)


def test_total_misses_do_not_leak_true_training_masks():
    agent = DQNAgent()
    sc = ScenarioConfig("training_missing", "train", "Missing", duration_steps=240)
    collect_episode(agent, sc, 32001, FaultProfile(miss_rate=1), epsilon=1, learn=False)
    for transition in agent.replay_buffer.tree.data:
        if transition is not None:
            assert np.all(transition[0][:12] == 0)
            assert transition[5].sum() == 1
            assert transition[5][transition[1]]


@pytest.mark.parametrize("duration,expected_decisions,partial_ticks", [(100, 0, 19), (101, 1, 0)])
def test_only_complete_macro_actions_enter_replay_at_timeout(duration, expected_decisions, partial_ticks):
    agent = DQNAgent()
    with torch.no_grad():
        for p in agent.online_net.parameters():
            p.zero_()
        agent.online_net.advantage_stream[-1].bias[0] = 1.
    row = collect_episode(agent, ScenarioConfig("train_timeout", "train", "Timeout",
                           duration_steps=duration), 32001, FaultProfile(), 0, learn=False)
    assert row["decisions"] == len(agent.replay_buffer) == expected_decisions
    assert row["dropped_partial_transition_ticks"] == partial_ticks
    if expected_decisions:
        transition = next(t for t in agent.replay_buffer.tree.data if t is not None)
        assert transition[7] == pytest.approx(train_policy.HP.GAMMA)
        assert transition[4] == 0  # Continuing task, not a fabricated terminal state.
        assert transition[3][17] == 0 and transition[3][16] >= .2


def test_research_reward_version_is_explicit_and_checkpoints_preserve_it(tmp_path):
    scenario = load_split("train")[0]
    env, _ = train_policy.build_environment(scenario)
    assert env.reward_version == train_policy.RESEARCH_REWARD_VERSION == "v5_single_switch_delay"
    agent = DQNAgent()
    agent.reward_version = train_policy.RESEARCH_REWARD_VERSION
    path = tmp_path / "v5.pt"
    torch.save(agent.get_checkpoint_state(), path)
    controller = D3QNController(checkpoint_path=str(path))
    assert controller.agent.reward_version == "v5_single_switch_delay"
    assert controller.checkpoint_metadata["reward_version"] == "v5_single_switch_delay"


def test_training_and_selection_reject_test_split():
    with pytest.raises(ValueError, match="test split"):
        load_split("test")
    with pytest.raises(ValueError, match="training scenarios"):
        collect_episode(DQNAgent(), ScenarioConfig("test_bad", "test", "Bad"),
                        1, FaultProfile(), 0)


def test_matched_control_includes_every_scheduled_candidate_in_order():
    assert candidate_labels(250, 100) == ["initial", "warmup", "100", "200", "250"]
    assert candidate_labels(200, 100) == ["initial", "warmup", "100", "200"]
    assert candidate_labels(2, 10) == ["initial", "warmup", "2"]
    with pytest.raises(ValueError):
        candidate_labels(0, 10)


def test_validation_does_not_change_training_rng():
    random.seed(10)
    np.random.seed(10)
    torch.manual_seed(10)
    expected = (random.random(), np.random.random(), torch.rand(1).item())
    random.seed(10)
    np.random.seed(10)
    torch.manual_seed(10)
    preserve_rng(lambda: (random.seed(99), np.random.seed(99), torch.manual_seed(99)))
    assert expected == (random.random(), np.random.random(), torch.rand(1).item())


def test_v7_checkpoint_and_sensor_only_features(tmp_path):
    agent = DQNAgent(36, OBSERVED_VERSION)
    path = tmp_path / "v7.pt"
    torch.save(agent.get_checkpoint_state(), path)
    controller = D3QNController(checkpoint_path=str(path))
    assert controller.agent.state_dim == 36
    ctx = ControllerContext(timestep=100, current_phase=0, time_in_phase=10,
                            can_switch_phase=True, is_decision_step=True,
                            outgoing_counts={"north": 15}, phase_starvation_times={2: 22.5},
                            valid_action_mask=np.ones(4, dtype=bool))
    state = encode_policy_observation(np.zeros(28), ctx, OBSERVED_VERSION)
    assert state[28] == pytest.approx(np.tanh(1))
    assert state[34] == .5
    assert 0 <= controller.act(np.zeros(28), ctx) < 4


def test_v7_collection_matches_inference():
    agent = DQNAgent(36, OBSERVED_VERSION)
    sc = ScenarioConfig("training_parity_v7", "train", "Parity", duration_steps=500)
    collected = collect_episode(agent, sc, 32001, FaultProfile(), epsilon=0, learn=False)
    result = ExperimentRunner().run(D3QNController(agent=agent), sc, 32001,
                                    record_trajectory=False, allow_untrained=True)
    assert collected["avg_delay"] == pytest.approx(result.avg_delay, abs=.001)
    assert next(t for t in agent.replay_buffer.tree.data if t is not None)[0].shape == (36,)


@pytest.mark.parametrize("miss_rate", [0., .3])
def test_shield_aware_collection_matches_wrapped_inference(miss_rate):
    agent = DQNAgent(36, OBSERVED_VERSION)
    # Deliberately prefer phase 0 so the shield must intervene in this test.
    with torch.no_grad():
        for parameter in agent.online_net.parameters():
            parameter.zero_()
        agent.online_net.advantage_stream[-1].bias[0] = 1.
    scenario = ScenarioConfig("training_shield_parity", "train", "Shield parity", duration_steps=1500)
    fault = FaultProfile(miss_rate=miss_rate, latency_ms=200)
    collected = collect_episode(agent, scenario, 32001, fault, epsilon=0, learn=False,
                                train_with_shield=True)
    from research.noise.fault_injector import PerceptionFaultInjector
    controller = FlowSyncUQController(d3qn_controller=D3QNController(agent=agent),
                                     enable_shield=True, enable_fallback=False)
    evaluated = ExperimentRunner().run(controller, scenario, 32001, record_trajectory=False,
                                      allow_untrained=True,
                                      fault_injector=PerceptionFaultInjector(fault, seed=122001))
    assert collected["avg_delay"] == pytest.approx(evaluated.avg_delay, abs=.001)
    assert collected["shield_audit"]["total_overrides"] > 0
    assert collected["shield_audit"] == evaluated.controller_diagnostics["shield"]
    assert evaluated.fallback_steps == 0
    for transition in agent.replay_buffer.tree.data:
        if transition is not None:
            assert transition[5][transition[1]]  # Replay labels are admissible proposals.


def test_shield_training_validation_scores_the_wrapped_policy(tmp_path, monkeypatch):
    calls = []

    def controller(name, **kwargs):
        calls.append((name, kwargs))
        return object()

    monkeypatch.setattr(train_policy, "get_controller", controller)
    monkeypatch.setattr(train_policy.torch, "load", lambda *a, **kw: {"obs_version": OBSERVED_VERSION})
    monkeypatch.setattr(train_policy, "load_split", lambda _: [ScenarioConfig("val_one", "validation", "One")])
    monkeypatch.setattr(train_policy, "VALIDATION_FAULTS", (FaultProfile(),))
    monkeypatch.setattr(train_policy.ExperimentRunner, "run", lambda *a, **kw: SimpleNamespace(
        avg_delay=3., p95_delay=4., total_vehicles_passed=10, executed_conflict_violations=0,
        executed_clearance_violations=0, starvation_count=0, checkpoint_hash="fake", arrival_trace_hash="fake",
        safety_samples=100, num_steps=100))
    assert train_policy.validation("policy.pt", tmp_path, "shield", seeds=[1], train_with_shield=True) == 3.
    assert calls == [("flowsync_uq", {"checkpoint_path": "policy.pt", "enable_shield": True,
                                     "enable_fallback": False})]
    payload = json.loads((tmp_path / "validation_shield.json").read_text())
    assert payload["selection_controller"] == "d3qn_shield"
    assert payload["rows"][0]["controller"] == "d3qn_shield"


def test_domain_randomization_is_seeded_and_does_not_mutate_templates():
    template = load_split("train")[0]
    before = template.to_dict()
    a = training_scenario(template, np.random.default_rng(7), 3000, True)
    b = training_scenario(template, np.random.default_rng(7), 3000, True)
    assert a.to_dict() == b.to_dict()
    assert template.to_dict() == before
    assert a.duration_steps == 3000
    assert a.demand_profile.turn_ratios != template.demand_profile.turn_ratios
    assert .2 <= a.demand_profile.base_lambda <= 1.2
    with pytest.raises(ValueError, match="training template"):
        training_scenario(ScenarioConfig("bad", "test", "Bad"), np.random.default_rng(7), 3000, True)


def test_runtime_budget_uses_elapsed_time_and_zero_disables_limit():
    now = [5.]
    budget = RunBudget(10, clock=lambda: now[0])
    unlimited = RunBudget(0, clock=lambda: now[0])
    now[0] = 14.99
    budget.check("demonstrations")
    now[0] = 15.
    with pytest.raises(BudgetExceeded, match="pretraining"):
        budget.check("pretraining")
    unlimited.check("validation")
    for invalid in (-1, float("inf"), float("nan")):
        with pytest.raises(ValueError, match="finite and nonnegative"):
            RunBudget(invalid)


def test_expired_collection_never_builds_environment(monkeypatch):
    now = [0.]
    budget = RunBudget(1, clock=lambda: now[0])
    now[0] = 2.
    monkeypatch.setattr(train_policy, "build_environment", lambda _: pytest.fail("Past deadline"))
    with pytest.raises(BudgetExceeded, match="training"):
        collect_episode(DQNAgent(), load_split("train")[0], 1, FaultProfile(), 0, budget=budget)


def test_interrupted_validation_records_partial_rows_without_score(tmp_path, monkeypatch):
    now = [0.]
    budget = RunBudget(1, clock=lambda: now[0])

    def run(*args, **kwargs):
        now[0] = 2.
        return SimpleNamespace(avg_delay=1, p95_delay=2, total_vehicles_passed=3,
                               executed_conflict_violations=0, executed_clearance_violations=0,
                               starvation_count=0, checkpoint_hash="fake", arrival_trace_hash="fake",
                               safety_samples=100, num_steps=100)

    monkeypatch.setattr(train_policy.ExperimentRunner, "run", run)
    monkeypatch.setattr(train_policy, "get_controller", lambda *a, **kw: object())
    monkeypatch.setattr(train_policy.torch, "load", lambda *a, **kw: {"obs_version": OBSERVED_VERSION})
    with pytest.raises(BudgetExceeded, match="validation_partial"):
        train_policy.validation("unused", tmp_path, "partial", budget=budget)
    data = json.loads((tmp_path / "validation_partial.json").read_text())
    assert data["complete"] is False and data["score"] is None
    assert len(data["rows"]) == 1


@pytest.mark.parametrize("stage", ["initialization", "validation_initial", "demonstrations",
                                  "imitation", "pretraining", "validation_warmup", "training",
                                  "validation_1", None])
def test_budget_stop_preserves_only_completed_selection(tmp_path, monkeypatch, stage):
    class StageBudget:
        elapsed = 10.

        def check(self, current):
            if current == stage:
                raise BudgetExceeded(current)

    def validate(checkpoint, output, label, **kwargs):
        kwargs["budget"].check(f"validation_{label}")
        return {"initial": 10., "warmup": 11., "1": 9.}[label]

    def collect(*args, **kwargs):
        return {"loss": None, "avg_delay": 1.}

    monkeypatch.setattr(train_policy, "validation", validate)
    monkeypatch.setattr(train_policy, "collect_episode", collect)
    args = SimpleNamespace(output=tmp_path, seed=1, validation_seeds=[1], demo_episodes=1,
                           demo_loss_weight=.1, demo_loss_final_weight=None, demo_loss_decay_episodes=0,
                           train_with_shield=False,
                           episode_steps=0, domain_randomization=False, clean_only=True,
                           imitation_updates=1, pretrain_updates=1, checkpoint=None,
                           episodes=1, validate_every=1, target_update=200)
    train_policy.run_training(args, DQNAgent(), np.random.default_rng(1), load_split("train"),
                              {"parent_sha256": None}, StageBudget())
    summary = json.loads((tmp_path / "summary.json").read_text())
    if stage is None:
        assert summary["stop_reason"] == "completed"
        assert summary["interrupted_checkpoint"] is None
        assert summary["episodes_completed"] == 1
        assert summary["best"]["score"] == 9.
        assert summary["best"]["path"].endswith("checkpoint_1.pt")
        return
    assert summary["stop_reason"] == "wall_clock_budget"
    assert summary["interrupted_stage"] == stage
    assert (tmp_path / "checkpoint_interrupted.pt").exists()
    if stage in ("initialization", "validation_initial"):
        assert summary["best"] is None
        assert not (tmp_path / "selection.json").exists()
    else:
        selection = json.loads((tmp_path / "selection.json").read_text())
        assert selection == summary["best"]
        assert selection["score"] == 10.
        assert selection["path"].endswith("checkpoint_initial.pt")
    assert summary["episodes_completed"] == (1 if stage == "validation_1" else 0)
