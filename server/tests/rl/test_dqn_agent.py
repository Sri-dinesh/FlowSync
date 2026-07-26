import pytest
import numpy as np
import torch
from app.rl.dqn_agent import DQNAgent

def test_dqn_agent_initialization():
    agent = DQNAgent()
    assert agent.online_net.feature_layer[0].in_features == 20
    assert agent.online_net.advantage_stream[-1].out_features == 4

def test_dqn_agent_select_action_random():
    agent = DQNAgent()
    state = np.zeros(20)
    # With epsilon 1.0, it should always be random
    action = agent.select_action(state, epsilon=1.0)
    assert 0 <= action < 4

def test_dqn_agent_select_action_greedy():
    agent = DQNAgent()
    state = np.zeros(20)
    # With epsilon 0.0, it should be greedy
    action = agent.select_action(state, epsilon=0.0)
    assert 0 <= action < 4

def test_dqn_agent_train_step():
    agent = DQNAgent()
    batch_size = 2
    batch = (
        torch.zeros((batch_size, 20)),
        torch.zeros(batch_size, dtype=torch.long),
        torch.ones(batch_size),
        torch.zeros((batch_size, 20)),
        torch.zeros(batch_size),
        torch.ones(batch_size), # weights
        [99999, 100000]         # indices
    )
    loss, td_errors = agent.train_step(batch)
    assert isinstance(loss, float)
    assert loss >= 0
    assert len(td_errors) == 2

def test_dqn_agent_get_q_values():
    agent = DQNAgent()
    state = np.zeros(20)
    q_values = agent.get_q_values(state)
    assert isinstance(q_values, list)
    assert len(q_values) == 4
    for q in q_values:
        assert isinstance(q, float)

def test_double_dqn_loss_runs_cleanly():
    agent = DQNAgent()
    batch_size = 2
    batch = (
        torch.zeros((batch_size, 20)),
        torch.zeros(batch_size, dtype=torch.long),
        torch.ones(batch_size),
        torch.zeros((batch_size, 20)),
        torch.zeros(batch_size),
        torch.ones(batch_size),
        [99999, 100000]
    )
    loss, td_errors = agent.train_step(batch)
    assert isinstance(loss, float)
