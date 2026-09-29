import pytest
import numpy as np
import torch
from app.rl.dqn_agent import DQNAgent
from app.rl.hyperparams import HyperParams

HP = HyperParams()

def test_dqn_agent_initialization():
    agent = DQNAgent()
    assert agent.online_net.feature_layer[0].in_features == HP.STATE_DIM
    assert agent.online_net.advantage_stream[-1].out_features == 4

def test_dqn_agent_select_action_random():
    agent = DQNAgent()
    state = np.zeros(HP.STATE_DIM)
    # With epsilon 1.0, it should always be random
    action = agent.select_action(state, epsilon=1.0)
    assert 0 <= action < 4

def test_dqn_agent_select_action_greedy():
    agent = DQNAgent()
    state = np.zeros(HP.STATE_DIM)
    # With epsilon 0.0, it should be greedy
    action = agent.select_action(state, epsilon=0.0)
    assert 0 <= action < 4

def test_dqn_agent_train_step():
    agent = DQNAgent()
    batch_size = 2
    batch = (
        torch.zeros((batch_size, HP.STATE_DIM)),
        torch.zeros(batch_size, dtype=torch.long),
        torch.ones(batch_size),
        torch.zeros((batch_size, HP.STATE_DIM)),
        torch.zeros(batch_size),
        torch.ones(batch_size), # weights
        [99999, 100000],        # indices
        torch.ones((batch_size, HP.ACTION_DIM), dtype=torch.bool),
        torch.ones((batch_size, HP.ACTION_DIM), dtype=torch.bool),
        torch.full((batch_size,), HP.GAMMA),
        torch.zeros(batch_size),
    )
    loss, td_errors = agent.train_step(batch)
    assert isinstance(loss, float)
    assert loss >= 0
    assert len(td_errors) == 2

def test_dqn_agent_get_q_values():
    agent = DQNAgent()
    state = np.zeros(HP.STATE_DIM)
    q_values = agent.get_q_values(state)
    assert isinstance(q_values, list)
    assert len(q_values) == 4
    for q in q_values:
        assert isinstance(q, float)

def test_double_dqn_loss_runs_cleanly():
    agent = DQNAgent()
    batch_size = 2
    batch = (
        torch.zeros((batch_size, HP.STATE_DIM)),
        torch.zeros(batch_size, dtype=torch.long),
        torch.ones(batch_size),
        torch.zeros((batch_size, HP.STATE_DIM)),
        torch.zeros(batch_size),
        torch.ones(batch_size),
        [99999, 100000],
        torch.ones((batch_size, HP.ACTION_DIM), dtype=torch.bool),
        torch.ones((batch_size, HP.ACTION_DIM), dtype=torch.bool),
        torch.full((batch_size,), HP.GAMMA),
        torch.zeros(batch_size),
    )
    loss, td_errors = agent.train_step(batch)
    assert isinstance(loss, float)
