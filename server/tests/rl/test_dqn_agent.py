import pytest
import numpy as np
import torch
from app.rl.dqn_agent import DQNAgent

def test_dqn_agent_initialization():
    agent = DQNAgent(state_dim=8, action_dim=4)
    assert agent.action_dim == 4
    assert agent.online_net.net[0].in_features == 8
    assert agent.online_net.net[-1].out_features == 4

def test_dqn_agent_select_action_random():
    agent = DQNAgent(state_dim=8, action_dim=4)
    state = np.zeros(8)
    # With epsilon 1.0, it should always be random
    action = agent.select_action(state, epsilon=1.0)
    assert 0 <= action < 4

def test_dqn_agent_select_action_greedy():
    agent = DQNAgent(state_dim=8, action_dim=4)
    state = np.zeros(8)
    # With epsilon 0.0, it should be greedy
    action = agent.select_action(state, epsilon=0.0)
    assert 0 <= action < 4

def test_dqn_agent_train_step():
    agent = DQNAgent(state_dim=8, action_dim=4)
    batch_size = 2
    batch = (
        torch.zeros((batch_size, 8)),
        torch.zeros(batch_size, dtype=torch.long),
        torch.ones(batch_size),
        torch.zeros((batch_size, 8)),
        torch.zeros(batch_size)
    )
    loss = agent.train_step(batch)
    assert isinstance(loss, float)
    assert loss >= 0
