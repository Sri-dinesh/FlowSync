import pytest
import numpy as np
import torch
from app.rl.replay_buffer import PrioritizedReplayBuffer

def test_replay_buffer_push():
    buffer = PrioritizedReplayBuffer(capacity=10)
    state = np.zeros(20)
    buffer.push(state, 0, 1.0, state, False)
    assert len(buffer) == 1

def test_replay_buffer_sample():
    buffer = PrioritizedReplayBuffer(capacity=10)
    state = np.zeros(20)
    for _ in range(5):
        buffer.push(state, 0, 1.0, state, False)
    
    states, actions, rewards, next_states, dones, weights, indices = buffer.sample(batch_size=3)
    assert states.shape == (3, 20)
    assert actions.shape == (3,)
    assert rewards.shape == (3,)
    assert next_states.shape == (3, 20)
    assert dones.shape == (3,)
    assert weights.shape == (3,)
    assert len(indices) == 3
