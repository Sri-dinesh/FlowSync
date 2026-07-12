import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from app.rl.dqn_network import DuelingDQNNetwork
from app.rl.replay_buffer import PrioritizedReplayBuffer
from app.rl.hyperparams import HyperParams

HP = HyperParams()


class DQNAgent:
    """
    Dueling Double DQN with Prioritized Experience Replay.

    Architecture combines:
    - Dueling DQN: V(s) + A(s,a) decomposition for better high-density decisions
    - Double DQN: online net selects action, target net evaluates (reduces overestimation)
    - PER: high-TD-error transitions sampled more often (learns from critical events faster)

    Based on: FPA-DQN (2025), 3DQN-PER (2025), Wang et al. 2016, Schaul et al. 2016
    """
    def __init__(self):
        self.online_net = DuelingDQNNetwork(HP.STATE_DIM, HP.ACTION_DIM)
        self.target_net = DuelingDQNNetwork(HP.STATE_DIM, HP.ACTION_DIM)
        self.target_net.load_state_dict(self.online_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(
            self.online_net.parameters(),
            lr=HP.LEARNING_RATE,
            eps=1e-8       # Adam epsilon — slightly larger for stability
        )
        self.loss_fn = nn.SmoothL1Loss(reduction='none')  # per-sample loss for PER weighting
        self.replay_buffer = PrioritizedReplayBuffer(HP.REPLAY_BUFFER_SIZE)
        self.step_count = 0

    def select_action(self, state: np.ndarray, epsilon: float) -> int:
        if np.random.random() < epsilon:
            return np.random.randint(HP.ACTION_DIM)
        state_tensor = torch.FloatTensor(state).unsqueeze(0)
        with torch.no_grad():
            q_values = self.online_net(state_tensor)
        return int(q_values.argmax().item())

    def get_q_values(self, state: np.ndarray) -> list:
        state_tensor = torch.FloatTensor(state).unsqueeze(0)
        with torch.no_grad():
            q_values = self.online_net(state_tensor)
        return q_values.squeeze(0).tolist()

    def train_step(self, batch) -> tuple[float, np.ndarray]:
        """
        Dueling Double DQN training step with PER importance sampling.

        Returns: (loss_value, td_errors) — td_errors used to update PER priorities.
        """
        states, actions, rewards, next_states, dones, weights, indices = batch

        # Current Q-values (online net)
        current_q_all = self.online_net(states)
        current_q = current_q_all.gather(1, actions.unsqueeze(1)).squeeze(1)

        with torch.no_grad():
            # Double DQN: online net selects best action for next state
            next_actions = self.online_net(next_states).argmax(1)
            # Target net evaluates that action
            next_q = self.target_net(next_states).gather(
                1, next_actions.unsqueeze(1)
            ).squeeze(1)
            # Bellman target
            target_q = rewards + HP.GAMMA * next_q * (1 - dones)

        # Per-sample loss (needed for PER priority update)
        td_errors = (target_q - current_q).detach().cpu().numpy()
        per_sample_loss = self.loss_fn(current_q, target_q)

        # Weight loss by importance sampling weights (PER correction)
        weighted_loss = (per_sample_loss * weights).mean()

        self.optimizer.zero_grad()
        weighted_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.online_net.parameters(), max_norm=10.0)
        self.optimizer.step()

        self.step_count += 1

        # Update PER priorities with new TD errors
        self.replay_buffer.update_priorities(indices, np.abs(td_errors))

        return float(weighted_loss.item()), td_errors

    def sync_target_network(self):
        self.target_net.load_state_dict(self.online_net.state_dict())

    def get_checkpoint_state(self) -> dict:
        return {
            'online_net': self.online_net.state_dict(),
            'target_net': self.target_net.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'step_count': self.step_count,
            'obs_version': 'v3_20dim_pressure',
        }

    def save(self, path: str):
        torch.save(self.get_checkpoint_state(), path)

    def load(self, path: str):
        checkpoint = torch.load(path, map_location='cpu')
        if isinstance(checkpoint, dict) and 'online_net' in checkpoint:
            self.online_net.load_state_dict(checkpoint['online_net'])
            self.target_net.load_state_dict(checkpoint['target_net'])
            if 'optimizer' in checkpoint:
                self.optimizer.load_state_dict(checkpoint['optimizer'])
            if 'step_count' in checkpoint:
                self.step_count = checkpoint['step_count']
        else:
            # Legacy format
            self.online_net.load_state_dict(checkpoint)
            self.sync_target_network()
        self.target_net.eval()
