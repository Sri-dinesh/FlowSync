from dataclasses import replace

import numpy as np
import pytest
import torch

from research.policies.ppo import ActorCritic, PPOController, save_checkpoint
from research.training.ppo import Transition, advantages, batch_data, clipped_loss, collect_episode, update
from research.training.train_policy import RunBudget, load_split
from research.pilots.run_switch_margin_pilot import PARENTS, PARENT_ROOT
from research.noise.fault_injector import FaultProfile, PerceptionFaultInjector
from server.app.controllers.base import ControllerContext


@pytest.fixture(autouse=True)
def single_thread():
    torch.set_num_threads(1)
    torch.manual_seed(42)


def transition(reward=1., ticks=20, value=0., next_value=0.):
    return Transition(np.zeros(36, np.float32), np.ones(4, bool), 0, float(np.log(.25)),
                      value, reward, ticks, next_value)


def test_variable_duration_gae_bootstraps_complete_last_gate_and_resets_episodes():
    first = transition(1, 20, 2, 3)
    last = transition(2, 40, 3, 4)
    a, returns = advantages([first, last])
    expected_last = 2 + .99**2*4 - 3
    assert a == pytest.approx([1+.99*3-2+.99*.95*expected_last, expected_last])
    assert returns == pytest.approx(a+[2, 3])
    separate = batch_data([[first], [last]])
    assert separate["returns"].tolist() == pytest.approx([1+.99*3, 2+.99**2*4])
    with pytest.raises(ValueError, match="Incomplete"):
        advantages([transition(ticks=19)])


def test_clipping_stops_improving_already_clipped_actions_but_corrects_wrong_direction():
    logp = torch.log(torch.tensor([1.5, .5, .5, 1.5], requires_grad=True))
    logp.retain_grad()
    loss = clipped_loss(logp, torch.zeros(4), torch.tensor([1., -1., 1., -1.]))
    loss.backward()
    assert logp.grad.tolist() == pytest.approx([0, 0, -.125, .375])


def test_masked_distribution_never_samples_invalid_actions_and_single_action_is_finite():
    model = ActorCritic()
    masks = torch.tensor([[False, True, False, False], [True, False, True, False]])
    policy = model.distribution(torch.zeros(2, 36), masks)
    samples = policy.sample((100,))
    assert samples[:, 0].eq(1).all() and ((samples[:, 1] == 0) | (samples[:, 1] == 2)).all()
    assert torch.isfinite(policy.log_prob(samples)).all() and torch.isfinite(policy.entropy()).all()
    with pytest.raises(ValueError, match="nonempty"):
        model.distribution(torch.zeros(1, 36), torch.zeros(1, 4, dtype=torch.bool))


@pytest.mark.parametrize("seed", list(PARENTS))
def test_parent_actor_initial_scores_and_greedy_actions_are_exact(seed):
    path = PARENT_ROOT/PARENTS[seed][0]
    if not path.exists():
        pytest.skip("Frozen local parent artifact is not distributed with source")
    payload = torch.load(path, weights_only=True, map_location="cpu")
    model = ActorCritic.from_parent(path)
    from server.app.rl.dqn_network import DuelingDQNNetwork
    original = DuelingDQNNetwork(36, 4)
    original.load_state_dict(payload["online_net"])
    states = torch.rand(60, 36)
    masks = torch.tensor([[bool(bits & (1 << i)) for i in range(4)] for bits in range(1, 16)]*4)
    with torch.no_grad():
        expected = original(states, masks)
        assert torch.equal(model.actor(states, masks), expected)
        assert torch.equal(model.distribution(states, masks).logits.argmax(1), expected.masked_fill(~masks, -torch.inf).argmax(1))


def test_critic_warmup_cannot_move_actor_and_policy_gradient_moves_rewarded_action():
    model = ActorCritic()
    actor = torch.optim.Adam([p for p in model.actor.parameters() if p.requires_grad], lr=.0001)
    critic = torch.optim.Adam(model.critic.parameters(), lr=.001)
    before = {key: value.clone() for key, value in model.actor.state_dict().items()}
    episode = [transition(reward=2., next_value=1.)]
    episode[0].log_probability = float(model.distribution(torch.zeros(1, 36), torch.ones(1, 4, dtype=torch.bool)).log_prob(torch.tensor([0])).detach()[0])
    logs = update(model, [episode], actor, critic, RunBudget(30), warmup=True)
    assert len(logs) == 20 and all(row["kind"] == "critic" for row in logs)
    assert all(torch.equal(value, before[key]) for key, value in model.actor.state_dict().items())
    assert model.values(torch.zeros(1, 36)).item() > 0
    states, masks = torch.rand(2, 36), torch.ones(2, 4, dtype=torch.bool)
    old = model.distribution(states, masks).probs[:, 0].detach()
    policy = model.distribution(states, masks)
    loss = clipped_loss(policy.log_prob(torch.zeros(2, dtype=torch.long)),
                        policy.log_prob(torch.zeros(2, dtype=torch.long)).detach(), torch.ones(2))
    actor.zero_grad(); loss.backward(); actor.step()
    assert (model.distribution(states, masks).probs[:, 0] > old).all()


def test_checkpoint_controller_uses_proposals_and_reports_policy_not_q_values(tmp_path):
    path = tmp_path/"ppo.pt"
    model = ActorCritic()
    save_checkpoint(path, model, dict(episode=0))
    controller = PPOController(path)
    ctx = ControllerContext(timestep=80, time_in_phase=8., valid_action_mask=np.array([False, True, False, False]))
    assert controller.act(np.zeros(28, np.float32), ctx) == 1
    assert controller.act(np.zeros(28, np.float32), replace(ctx, timestep=81, is_decision_step=False, current_phase=2)) == 2
    diagnostics = controller.get_diagnostics()
    assert diagnostics["checkpoint_loaded"] and len(diagnostics["checkpoint_hash"]) == 64
    assert "q_values" not in diagnostics and not controller.get_capabilities().to_dict()["produces_q_values"]
    from research.experiments.shielded_controller import ShieldedController
    assert not ShieldedController(controller).get_capabilities().to_dict()["produces_q_values"]
    incompatible = torch.load(path, weights_only=True)
    incompatible["schema_version"] = "wrong"
    torch.save(incompatible, path)
    with pytest.raises(ValueError, match="Incompatible"):
        PPOController(path)


def test_real_rollout_drops_incomplete_macro_and_keeps_sampling_rng_local():
    from research.scenarios.scenario_schema import ScenarioConfig
    template = load_split("train")[0].to_dict()
    template.update(duration_steps=115, scenario_hash="")
    scenario = ScenarioConfig.from_dict(template)
    model = ActorCritic()
    def run(global_seed):
        torch.manual_seed(global_seed)
        generator = torch.Generator().manual_seed(99)
        return collect_episode(model, scenario, 1330901, PerceptionFaultInjector(FaultProfile(), seed=1330901+90000),
                               generator, RunBudget(30))
    first, summary = run(2)
    second, again = run(456)
    assert [t.action for t in first] == [t.action for t in second]
    assert summary == again
    assert summary["signal_samples"] == 115 and summary["signal_violations"] == 0
    assert len(summary["proposals"]) == len(first)+int(summary["dropped_partial_ticks"]>0)
    assert all(t.ticks >= 20 for t in first)
    assert summary["dropped_partial_ticks"] > 0
    assert all(t.action == p["proposed"] for t, p in zip(first, summary["proposals"]))


def test_ppo_rejects_stale_behavior_likelihoods():
    model = ActorCritic()
    actor = torch.optim.Adam(model.actor.parameters())
    critic = torch.optim.Adam(model.critic.parameters())
    stale = transition()
    stale.log_probability = -100.
    with pytest.raises(ValueError, match="not on-policy"):
        update(model, [[stale]], actor, critic, RunBudget(30))


def test_shield_override_keeps_the_policy_proposal_in_the_training_record(monkeypatch):
    from research.scenarios.scenario_schema import ScenarioConfig
    from server.app.controllers.safety_shield import SafetyShield, ShieldDecision
    template = load_split("train")[0].to_dict()
    template.update(duration_steps=250, scenario_hash="")
    scenario = ScenarioConfig.from_dict(template)
    monkeypatch.setattr(SafetyShield, "filter_context", lambda self, proposed, ctx:
        ShieldDecision(proposed, ctx.current_phase, proposed != ctx.current_phase, "test_override"))
    rows, summary = collect_episode(ActorCritic(), scenario, 1330902,
        PerceptionFaultInjector(FaultProfile(), seed=1420902), torch.Generator().manual_seed(99), RunBudget(30))
    changed = [(t, p) for t, p in zip(rows, summary["proposals"]) if p["proposed"] != p["executed"]]
    assert changed and all(t.action == p["proposed"] and t.action != p["executed"] for t, p in changed)


def test_saved_batch_round_trip_keeps_proposals_and_completed_next_states(tmp_path):
    from research.pilots.run_ppo_restoration_pilot import store_batch, load_batch
    item = transition()
    item.next_state = np.ones(36, np.float32)
    path = tmp_path/"batch.npz"
    store_batch(path, [[item], []])
    restored = load_batch(path)
    assert len(restored) == 2 and restored[1] == []
    assert restored[0][0].action == item.action and restored[0][0].log_probability == item.log_probability
    assert np.array_equal(restored[0][0].next_state, item.next_state)


def test_full_panel_screen_requires_all_replicates_and_ignores_intermediate_winners():
    from research.pilots.run_ppo_restoration_pilot import comparison, baseline_jobs, validation_cases, STAGES
    cases = validation_cases()
    def row(parent, arm, stage, case, delay, baseline=None):
        return dict(parent=parent, arm=arm, stage=stage, case_id=case["case_id"], baseline=baseline,
                    delay=delay, p95=30., passed=100, samples=1200, violations=0, arrival_trace_hash=case["case_id"])
    workers = [dict(parent=p, arm=arm, complete=True, episodes=90, training_signal_audit=True, training_arrivals=["paired"]*90,
        evaluations=[row(p, arm, stage, c, (9. if arm=="restored" else 9.5) if stage==90 else 10.) for stage in STAGES for c in cases])
        for p in PARENTS for arm in ("raw", "restored")]
    baselines = [row(p, arm, "baseline", c, 10., name) for p, arm, name in baseline_jobs() for c in cases]
    assert comparison(workers, baselines)["continue_to_expanded_validation"]
    # A good aggregate must not hide one degrading replicate.
    for w in workers:
        for r in w["evaluations"]:
            if r["arm"]=="restored" and r["stage"]==90:
                r["delay"] = 10.2 if r["parent"]=="101" else 7.
    result = comparison(workers, baselines)
    assert result["primary"]["delay"] < 9 and not result["continue_to_expanded_validation"]
    assert not comparison(workers[:-1], baselines)["primary_endpoint_complete"]


def test_training_plan_is_paired_train_only_and_validation_seeds_are_disjoint():
    from research.pilots.run_ppo_restoration_pilot import training_cases, validation_cases
    cases = training_cases()
    assert cases == training_cases() and len(cases) == 90
    assert all(c["scenario"]["split"] == "train" and c["scenario"]["duration_steps"] == 1200 for c in cases)
    for start in range(0, 90, 6):
        assert len({c["scenario"]["scenario_id"] for c in cases[start:start+6]}) == 6
    assert not {c["seed"] for c in cases} & {c["seed"] for c in validation_cases()}
