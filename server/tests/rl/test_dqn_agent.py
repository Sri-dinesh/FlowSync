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


def test_td_target_uses_masked_double_q_duration_discount_and_terminal_flag():
    class FixedQ(torch.nn.Module):
        def __init__(self, values):
            super().__init__()
            self.values = torch.nn.Parameter(torch.tensor(values, dtype=torch.float32))

        def forward(self, states, valid_action_mask=None):
            return self.values.expand(len(states), -1)

    agent = DQNAgent()
    agent.online_net = FixedQ([1., 3., 9., 7.])
    agent.target_net = FixedQ([10., 20., 100., 40.])
    agent.optimizer = torch.optim.SGD(agent.online_net.parameters(), lr=0.)
    batch = (
        torch.zeros((3, HP.STATE_DIM)), torch.tensor([0, 1, 2]), torch.tensor([1., 2., 3.]),
        torch.zeros((3, HP.STATE_DIM)), torch.tensor([0., 1., 0.]), torch.ones(3),
        [99999, 100000, 100001], torch.ones((3, 4), dtype=torch.bool),
        torch.tensor([[True, True, False, False], [True, True, True, True],
                      [False, False, False, True]]),
        torch.tensor([.9, .5, .5]), torch.zeros(3),
    )
    _, errors = agent.train_step(batch)
    # Online chooses allowed action 1 (not masked-out 2); target evaluates it.
    # True terminal sample does not bootstrap. Final sample has a 0.5 discount.
    np.testing.assert_allclose(errors, [18., -1., 14.], atol=1e-6)
    assert agent.latest_q_stats["demo_sample_fraction"] == 0.
    assert agent.latest_q_stats["weighted_demo_loss"] == 0.


@pytest.mark.parametrize("weight", [1., .1])
def test_loss_scale_telemetry_distinguishes_weighting_from_prediction_error(weight):
    class FixedQ(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.values = torch.nn.Parameter(torch.zeros(4))

        def forward(self, states, valid_action_mask=None):
            return self.values.expand(len(states), -1)

    agent = DQNAgent()
    agent.online_net, agent.target_net = FixedQ(), FixedQ()
    agent.optimizer = torch.optim.SGD(agent.online_net.parameters(), lr=.1)
    batch = (torch.zeros((2, HP.STATE_DIM)), torch.zeros(2, dtype=torch.long), torch.full((2,), 2.),
        torch.zeros((2, HP.STATE_DIM)), torch.ones(2), torch.full((2,), weight),
        [99999, 100000], torch.ones((2, 4), dtype=torch.bool), torch.ones((2, 4), dtype=torch.bool),
        torch.full((2,), .99), torch.zeros(2))
    loss, errors = agent.train_step(batch)
    np.testing.assert_allclose(errors, 2.)
    stats = agent.latest_q_stats
    assert stats["unweighted_td_loss"] == 1.5
    assert stats["td_loss"] == pytest.approx(1.5*weight)
    assert loss == pytest.approx(1.5*weight)
    assert stats["pre_clip_gradient_norm"] == pytest.approx(weight)
    assert stats["importance_weight_min"] == stats["importance_weight_max"] == weight
    # Instrumentation leaves the expected original SGD update unchanged.
    torch.testing.assert_close(agent.online_net.values, torch.tensor([.1*weight, 0., 0., 0.]))
