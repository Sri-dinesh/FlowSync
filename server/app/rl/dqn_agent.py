from typing import Tuple

import numpy as np
import torch
from torch import nn

from .dqn_network import DQNNetwork
from .replay_buffer import ReplayBuffer


class DQNAgent:
    def __init__(
        self,
        state_dim: int = 8,
        action_dim: int = 4,
        learning_rate: float = 1e-3,
        gamma: float = 0.95,
        replay_buffer_size: int = 10_000,
    ) -> None:
        self.action_dim = action_dim
        self.gamma = gamma
        self.online_net = DQNNetwork(state_dim, action_dim)
        self.target_net = DQNNetwork(state_dim, action_dim)
        self.target_net.load_state_dict(self.online_net.state_dict())
        self.optimizer = torch.optim.Adam(self.online_net.parameters(), lr=learning_rate)
        self.replay_buffer = ReplayBuffer(maxlen=replay_buffer_size)
        self.loss_fn = nn.MSELoss()

    def select_action(self, state: np.ndarray, epsilon: float) -> int:
        if np.random.rand() < epsilon:
            return int(np.random.randint(self.action_dim))

        state_tensor = torch.tensor(state, dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            q_values = self.online_net(state_tensor)
        return int(torch.argmax(q_values, dim=1).item())

    def train_step(
        self,
        batch: Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor],
    ) -> float:
        states, actions, rewards, next_states, dones = batch
        actions = actions.unsqueeze(1)

        q_values = self.online_net(states).gather(1, actions).squeeze(1)

        with torch.no_grad():
            next_q_values = self.target_net(next_states).max(1)[0]
            targets = rewards + (1 - dones) * self.gamma * next_q_values

        loss = self.loss_fn(q_values, targets)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        return float(loss.item())

    def sync_target_network(self) -> None:
        self.target_net.load_state_dict(self.online_net.state_dict())

    def save(self, path: str) -> None:
        torch.save(self.online_net.state_dict(), path)

    def load(self, path: str) -> None:
        self.online_net.load_state_dict(torch.load(path, map_location="cpu"))
        self.sync_target_network()
