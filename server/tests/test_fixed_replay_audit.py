"""Verify diagnostic algebra without changing production learning semantics."""
import copy
import json

import numpy as np
import pytest
import torch
import torch.nn.functional as F

from research.audits.audit_fixed_replay import (ARMS, SEEDS, STEPS, batch_for, bellman_targets,
    load_cases, metrics, new_agent, summarize, tensorize)
from server.app.rl.dqn_agent import DQNAgent


@pytest.fixture
def dataset():
    rng = np.random.default_rng(451)
    transitions = []
    for i in range(12):
        mask = np.array([True, True, i%2==0, False])
        transitions.append((rng.normal(size=36), i%2, float(-i), rng.normal(size=36),
                            float(i==0), mask, mask, .91, float(i%3==0)))
    return tensorize(transitions)


def parent():
    torch.manual_seed(123)
    agent = DQNAgent(36, "v7_36dim_observed")
    return dict(obs_version="v7_36dim_observed", online_net=copy.deepcopy(agent.online_net.state_dict()))


def test_frozen_adapter_matches_explicit_joint_objective_and_optimizer(dataset):
    checkpoint = parent()
    actual, reference = new_agent(checkpoint), new_agent(checkpoint)
    labels = bellman_targets(actual, dataset)
    ids = torch.arange(12)
    batch = batch_for(dataset, ids, labels)
    assert torch.equal(batch[2], labels) and batch[4].eq(1).all() and batch[9].eq(0).all()
    assert batch[5].eq(1).all() and batch[6] == []
    assert dataset["dones"].sum() == 1 and dataset["discounts"].gt(0).all()
    actual.train_step(batch)
    q = reference.online_net(dataset["states"], valid_action_mask=dataset["masks"])
    chosen = q.gather(1,dataset["actions"][:,None]).squeeze(1)
    other = q.masked_fill(~dataset["masks"],-torch.inf).scatter(1,dataset["actions"][:,None],-torch.inf)
    margin = F.relu(.5 + other.max(1).values-chosen)
    loss = F.smooth_l1_loss(chosen,labels) + .5*(margin*dataset["demos"]).sum()/dataset["demos"].sum()
    reference.optimizer.zero_grad()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(reference.online_net.parameters(),10.)
    reference.optimizer.step()
    for key,value in actual.online_net.state_dict().items():
        torch.testing.assert_close(value, reference.online_net.state_dict()[key], rtol=0,atol=0)
        assert torch.equal(actual.target_net.state_dict()[key],checkpoint["online_net"][key])
    assert len(actual.replay_buffer) == 0


def test_live_targets_respect_terminal_and_mask(dataset):
    agent = new_agent(parent())
    targets = bellman_targets(agent,dataset)
    assert targets[0] == dataset["rewards"][0]
    with torch.no_grad():
        q = agent.online_net(dataset["next_states"],valid_action_mask=dataset["next_masks"])
        best = q.masked_fill(~dataset["next_masks"],-torch.inf).argmax(1)
        assert dataset["next_masks"].gather(1,best[:,None]).all()
        expected = dataset["rewards"]+dataset["discounts"]*(1-dataset["dones"])*q.gather(1,best[:,None]).squeeze(1)
    torch.testing.assert_close(targets,expected)
    batch = batch_for(dataset,torch.arange(12))
    assert torch.equal(batch[2],dataset["rewards"]) and torch.equal(batch[4],dataset["dones"])


def test_metrics_do_not_mutate_weights_or_data(dataset):
    agent = new_agent(parent())
    weights = copy.deepcopy(agent.online_net.state_dict())
    original = {k:v.clone() for k,v in dataset.items()}
    labels = bellman_targets(agent,dataset)
    with torch.no_grad():
        actions=agent.online_net(dataset["states"],valid_action_mask=dataset["masks"]).masked_fill(
            ~dataset["masks"],-torch.inf).argmax(1)
    result=metrics(agent,dataset,labels,actions)
    assert result["target_drift_mae"]==0 and result["action_disagreement"]==0
    assert all(torch.equal(v,agent.online_net.state_dict()[k]) for k,v in weights.items())
    assert all(torch.equal(v,dataset[k]) for k,v in original.items())


def test_summary_rejects_missing_or_unpaired_data():
    rows=[dict(seed=s,arm=a,updates=u,dataset_sha256=str(s),
               metrics={p:dict(fixed_label_mae=1.) for p in ("fit","probe")})
          for s in SEEDS for a in ARMS for u in STEPS]
    assert summarize(rows)["curves"]==45
    with pytest.raises(ValueError,match="Incomplete"):
        summarize(rows[:-1])
    rows[0]["dataset_sha256"]="changed"
    with pytest.raises(ValueError,match="Unmatched datasets"):
        summarize(rows)


def test_case_loader_rejects_nontraining_inputs(tmp_path):
    scenario=dict(scenario_id="test_fixture", split="test",name="fixture",description="fixture",
                  duration_steps=1200,topology="single_intersection",demand_profile={})
    row=dict(executed_scenario=scenario,seed=1,fault={})
    (tmp_path/"demonstrations.jsonl").write_text("\n".join(json.dumps(row) for _ in range(6)))
    (tmp_path/"training.jsonl").write_text("\n".join(json.dumps(dict(row,episode=e)) for e in (1,16,31,46,61,76)))
    with pytest.raises(ValueError,match="Only training"):
        load_cases(tmp_path)
