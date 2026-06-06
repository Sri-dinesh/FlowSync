import pytest
import numpy as np
import torch
from app.rl.replay_buffer import ReplayBuffer

def test_replay_buffer_push():
    buffer = ReplayBuffer(maxlen=10)
    state = np.zeros(8)
    buffer.push(state, 0, 1.0, state, False)
    assert len(buffer) == 1

def test_replay_buffer_sample():
    buffer = ReplayBuffer(maxlen=10)
    state = np.zeros(8)
    for _ in range(5):
        buffer.push(state, 0, 1.0, state, False)
    
    states, actions, rewards, next_states, dones = buffer.sample(batch_size=3)
    assert states.shape == (3, 8)
    assert actions.shape == (3,)
    assert rewards.shape == (3,)
    assert next_states.shape == (3, 8)
    assert dones.shape == (3,)
    assert isinstance(states, torch.Tensor)
