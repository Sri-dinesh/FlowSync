from typing import Tuple, List, Dict, Any
import numpy as np
import torch
from torch import nn
import torch.optim as optim

from .dqn_network import DQNNetwork
from .replay_buffer import ReplayBuffer
from .hyperparams import HyperParams

HP = HyperParams()


class DQNAgent:
    def __init__(
        self,
        state_dim: int = 8,
        action_dim: int = 4,
        learning_rate: float = 5e-4,
        gamma: float = 0.95,
        replay_buffer_size: int = 50_000,
    ) -> None:
        self.action_dim = action_dim
        self.gamma = gamma
        self.online_net = DQNNetwork(state_dim, action_dim)
        self.target_net = DQNNetwork(state_dim, action_dim)
        self.target_net.load_state_dict(self.online_net.state_dict())
        self.target_net.eval()  # target net never trains directly

        self.optimizer = optim.Adam(
            self.online_net.parameters(),
            lr=learning_rate
        )
        self.loss_fn = nn.SmoothL1Loss()  # Huber Loss — replaces MSELoss
        self.replay_buffer = ReplayBuffer(replay_buffer_size)
        self.step_count = 0

    def select_action(self, state: np.ndarray, epsilon: float) -> int:
        """Epsilon-greedy action selection."""
        if np.random.random() < epsilon:
            return int(np.random.randint(self.action_dim))
        state_tensor = torch.FloatTensor(state).unsqueeze(0)
        with torch.no_grad():
            q_values = self.online_net(state_tensor)
        return int(q_values.argmax().item())

    def get_q_values(self, state: np.ndarray) -> List[float]:
        """Return raw Q-values for all actions (used for dashboard display)."""
        state_tensor = torch.FloatTensor(state).unsqueeze(0)
        with torch.no_grad():
            q_values = self.online_net(state_tensor)
        return q_values.squeeze(0).numpy().tolist()

    def train_step(
        self,
        batch: Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor],
    ) -> float:
        """
        Double DQN training step.

        Standard DQN:
            target = r + γ * max_a[target_net(s')]

        Double DQN (fixes overestimation):
            best_action = argmax_a[online_net(s')]   ← online selects action
            target = r + γ * target_net(s')[best_action]  ← target evaluates it
        """
        states, actions, rewards, next_states, dones = batch

        # Current Q-values from online network
        current_q = self.online_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)

        with torch.no_grad():
            # DOUBLE DQN: online net selects best action for next state
            best_next_actions = self.online_net(next_states).argmax(1)
            # Target net evaluates that action (reduces overestimation)
            next_q = self.target_net(next_states).gather(
                1, best_next_actions.unsqueeze(1)
            ).squeeze(1)
            # Bellman target
            target_q = rewards + self.gamma * next_q * (1 - dones)

        loss = self.loss_fn(current_q, target_q)

        self.optimizer.zero_grad()
        loss.backward()
        # Gradient clipping — prevents exploding gradients
        torch.nn.utils.clip_grad_norm_(self.online_net.parameters(), max_norm=10.0)
        self.optimizer.step()

        self.step_count += 1
        return float(loss.item())

    def sync_target_network(self) -> None:
        """Hard update: copy online weights to target."""
        self.target_net.load_state_dict(self.online_net.state_dict())

    def get_checkpoint_state(self) -> Dict[str, Any]:
        return {
            'online_net': self.online_net.state_dict(),
            'target_net': self.target_net.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'step_count': self.step_count,
        }

    def save(self, path: str) -> None:
        torch.save(self.get_checkpoint_state(), path)

    def load(self, path: str) -> None:
        checkpoint = torch.load(path, map_location='cpu')
        if isinstance(checkpoint, dict) and 'online_net' in checkpoint:
            self.online_net.load_state_dict(checkpoint['online_net'])
            self.target_net.load_state_dict(checkpoint['target_net'])
            if 'optimizer' in checkpoint:
                self.optimizer.load_state_dict(checkpoint['optimizer'])
            if 'step_count' in checkpoint:
                self.step_count = checkpoint['step_count']
        else:
            # Old format (raw state dict)
            self.online_net.load_state_dict(checkpoint)
            self.sync_target_network()
        self.target_net.eval()
