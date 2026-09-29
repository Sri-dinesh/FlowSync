import pytest
import numpy as np
import torch
from app.rl.replay_buffer import PrioritizedReplayBuffer
from app.rl.hyperparams import HyperParams

HP = HyperParams()

def test_replay_buffer_push():
    buffer = PrioritizedReplayBuffer(capacity=10)
    state = np.zeros(HP.STATE_DIM)
    buffer.push(state, 0, 1.0, state, False)
    assert len(buffer) == 1

def test_replay_buffer_sample():
    buffer = PrioritizedReplayBuffer(capacity=10)
    state = np.zeros(HP.STATE_DIM)
    for _ in range(5):
        buffer.push(state, 0, 1.0, state, False)
    
    (
        states, actions, rewards, next_states, dones, weights, indices,
        masks, next_masks, discounts, demo_flags,
    ) = buffer.sample(batch_size=3)
    assert states.shape == (3, HP.STATE_DIM)
    assert actions.shape == (3,)
    assert rewards.shape == (3,)
    assert next_states.shape == (3, HP.STATE_DIM)
    assert dones.shape == (3,)
    assert weights.shape == (3,)
    assert len(indices) == 3
    assert masks.shape == (3, HP.ACTION_DIM)
    assert next_masks.shape == (3, HP.ACTION_DIM)
    assert discounts.shape == (3,)
    assert demo_flags.shape == (3,)
