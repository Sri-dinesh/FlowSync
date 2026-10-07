"""Dueling Double DQN Agent with action masking and prioritized experience replay."""
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import logging
from typing import Dict, Optional, Tuple
try:
    from .dqn_network import DuelingDQNNetwork
    from .replay_buffer import PrioritizedReplayBuffer
    from .hyperparams import HyperParams
except (ImportError, ValueError):
    from app.rl.dqn_network import DuelingDQNNetwork
    from app.rl.replay_buffer import PrioritizedReplayBuffer
    from app.rl.hyperparams import HyperParams

logger = logging.getLogger(__name__)

HP = HyperParams()


class DQNAgent:
    """
    Dueling Double DQN with Prioritized Experience Replay and Action Masking.

    Architecture combines:
    - Dueling DQN: V(s) + A(s,a) decomposition with masked advantage centering
    - Double DQN: online net selects action (masked), target net evaluates
    - PER: prioritized experience replay with importance sampling correction
    """

    def __init__(self):
        self.online_net = DuelingDQNNetwork(HP.STATE_DIM, HP.ACTION_DIM)
        self.target_net = DuelingDQNNetwork(HP.STATE_DIM, HP.ACTION_DIM)
        self.target_net.load_state_dict(self.online_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(
            self.online_net.parameters(),
            lr=HP.LEARNING_RATE,
            eps=1e-8,
        )
        self.loss_fn = nn.SmoothL1Loss(reduction="none")
        self.replay_buffer = PrioritizedReplayBuffer(HP.REPLAY_BUFFER_SIZE)
        self.step_count = 0
        self.total_train_steps = 0
        self.all_masked_fallback_count = 0
        self.latest_q_stats: Dict[str, float] = {}

    def prepare_for_finetuning(self, learning_rate: float = 1e-4) -> None:
        """
        Prepare agent for fine-tuning on a specialized scenario:
        1. Preserves learned weights in online_net and target_net.
        2. Re-initializes optimizer with reduced learning rate (default 1e-4) and fresh Adam moments.
        3. Clears replay buffer to remove stale generic experiences.
        4. Resets training step counters.
        """
        self.optimizer = optim.Adam(
            self.online_net.parameters(),
            lr=learning_rate,
            eps=1e-8,
        )
        self.replay_buffer = PrioritizedReplayBuffer(HP.REPLAY_BUFFER_SIZE)
        self.step_count = 0
        self.total_train_steps = 0
        logger.info(
            "DQNAgent primed for fine-tuning: lr=%.6f, replay buffer reset, online weights preserved",
            learning_rate,
        )

    def reset_for_fresh_training(self) -> None:
        """Discard weights, optimizer moments and replay for a genuinely fresh run."""
        self.online_net = DuelingDQNNetwork(HP.STATE_DIM, HP.ACTION_DIM)
        self.target_net = DuelingDQNNetwork(HP.STATE_DIM, HP.ACTION_DIM)
        self.target_net.load_state_dict(self.online_net.state_dict())
        self.target_net.eval()
        self.optimizer = optim.Adam(
            self.online_net.parameters(), lr=HP.LEARNING_RATE, eps=1e-8
        )
        self.replay_buffer = PrioritizedReplayBuffer(HP.REPLAY_BUFFER_SIZE)
        self.step_count = 0
        self.total_train_steps = 0
        self.all_masked_fallback_count = 0
        self.latest_q_stats = {}

    def select_action(
        self,
        state: np.ndarray,
        epsilon: float,
        valid_action_mask: Optional[np.ndarray] = None,
    ) -> int:
        """
        ε-greedy action selection with optional action masking (BUG-05).

        Args:
            state: Observation array.
            epsilon: Exploration probability.
            valid_action_mask: bool array [action_dim]. If provided, invalid actions
                are excluded from both random exploration and argmax selection.

        Returns:
            Selected action index.
        """
        if valid_action_mask is None:
            valid_action_mask = np.ones(HP.ACTION_DIM, dtype=bool)

        valid_indices = np.where(valid_action_mask)[0]
        if len(valid_indices) == 0:
            self.all_masked_fallback_count += 1
            logger.warning(
                "Action masking: all actions masked out (count=%d); falling back to all valid",
                self.all_masked_fallback_count,
            )
            valid_indices = np.arange(HP.ACTION_DIM)  # safety fallback
            valid_action_mask = np.ones(HP.ACTION_DIM, dtype=bool)

        if np.random.random() < epsilon:
            return int(np.random.choice(valid_indices))

        expected_dim = self.online_net.feature_layer[0].in_features
        if len(state) < expected_dim:
            state = np.pad(state, (0, expected_dim - len(state)), mode="constant")
        elif len(state) > expected_dim:
            state = state[:expected_dim]

        state_tensor = torch.FloatTensor(state).unsqueeze(0)
        mask_tensor = torch.BoolTensor(valid_action_mask).unsqueeze(0)

        with torch.no_grad():
            q_values = self.online_net(state_tensor, valid_action_mask=mask_tensor)

        q_values_masked = q_values.clone()
        q_values_masked[0, ~valid_action_mask] = float("-inf")

        return int(q_values_masked.argmax().item())

    def get_q_values(
        self,
        state: np.ndarray,
        valid_action_mask: Optional[np.ndarray] = None,
    ) -> list:
        expected_dim = self.online_net.feature_layer[0].in_features
        if len(state) < expected_dim:
            state = np.pad(state, (0, expected_dim - len(state)), mode="constant")
        elif len(state) > expected_dim:
            state = state[:expected_dim]

        state_tensor = torch.FloatTensor(state).unsqueeze(0)
        mask_tensor = (
            torch.BoolTensor(valid_action_mask).unsqueeze(0)
            if valid_action_mask is not None
            else None
        )
        with torch.no_grad():
            q_values = self.online_net(state_tensor, valid_action_mask=mask_tensor)
        return q_values.squeeze(0).tolist()

    def train_step(self, batch) -> tuple[float, np.ndarray]:
        """
        Dueling Double DQN training step with PER importance sampling and action masking.

        BUG-05 fix:
          - Masked advantage centering during forward pass (via DuelingDQNNetwork).
          - Masked Double-DQN target: next_actions selected only among valid actions.
            Valid actions for next state are approximated via action masks stored in PER.

        Returns: (loss_value, td_errors) — td_errors used to update PER priorities.
        """
        (
            states, actions, rewards, next_states, dones, weights, indices,
            action_masks, next_action_masks, bootstrap_discounts, demo_flags,
        ) = batch

        current_q_all = self.online_net(states, valid_action_mask=action_masks)
        current_q = current_q_all.gather(1, actions.unsqueeze(1)).squeeze(1)

        with torch.no_grad():
            # Double DQN: online network selects action, target network evaluates
            next_q_online = self.online_net(
                next_states, valid_action_mask=next_action_masks
            )
            next_q_masked = next_q_online.clone()
            next_q_masked[~next_action_masks] = float("-inf")
            next_actions = next_q_masked.argmax(1)

            next_q_target = self.target_net(
                next_states, valid_action_mask=next_action_masks
            )
            next_q = next_q_target.gather(1, next_actions.unsqueeze(1)).squeeze(1)

            target_q = rewards + bootstrap_discounts * next_q * (1 - dones)

        # Per-sample loss for prioritized experience replay weights
        td_errors = (target_q - current_q).detach().cpu().numpy()
        per_sample_loss = self.loss_fn(current_q, target_q)

        # Weight loss by importance sampling weights for PER bias correction
        td_loss = (per_sample_loss * weights).mean()

        # Large-margin penalty prevents unvisited actions from being overestimated on warm-start transitions.
        other_q = current_q_all.clone()
        other_q[~action_masks] = float("-inf")
        other_q.scatter_(1, actions.unsqueeze(1), float("-inf"))
        has_alternative = action_masks.sum(dim=1) > 1
        best_other_q = other_q.max(dim=1).values
        margin_loss_per_sample = torch.where(
            has_alternative,
            torch.relu(0.5 + best_other_q - current_q),
            torch.zeros_like(current_q),
        )
        demo_weight = demo_flags * has_alternative.float()
        demo_loss = (
            (margin_loss_per_sample * demo_weight).sum()
            / demo_weight.sum().clamp(min=1.0)
        )
        weighted_loss = td_loss + 0.10 * demo_loss

        self.optimizer.zero_grad()
        weighted_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.online_net.parameters(), max_norm=10.0)
        self.optimizer.step()

        self.step_count += 1
        self.total_train_steps += 1

        with torch.no_grad():
            q_mean = float(current_q.mean().item())
            q_std = float(current_q.std().item()) if len(current_q) > 1 else 0.0
            q_max = float(current_q.max().item())
            q_min = float(current_q.min().item())

        self.latest_q_stats = {
            "q_mean": round(q_mean, 4),
            "q_std": round(q_std, 4),
            "q_max": round(q_max, 4),
            "q_min": round(q_min, 4),
            "td_error_mean": round(float(np.mean(np.abs(td_errors))), 4),
            "td_error_max": round(float(np.max(np.abs(td_errors))), 4),
            "loss": round(float(weighted_loss.item()), 5),
            "td_loss": round(float(td_loss.item()), 5),
            "demo_margin_loss": round(float(demo_loss.item()), 5),
        }

        self.replay_buffer.update_priorities(indices, np.abs(td_errors))

        return float(weighted_loss.item()), td_errors

    def sync_target_network(self):
        self.target_net.load_state_dict(self.online_net.state_dict())

    def get_checkpoint_state(self) -> dict:
        return {
            "online_net":        self.online_net.state_dict(),
            "target_net":        self.target_net.state_dict(),
            "optimizer":         self.optimizer.state_dict(),
            "step_count":        self.step_count,
            "total_train_steps": self.total_train_steps,
            "obs_version":       HP.OBS_VERSION,
            "reward_version":    "v4_incremental_delay",
            "demand_version":    "v2_total_lambda_with_upstream_backlog",
        }

    def save(self, path: str):
        torch.save(self.get_checkpoint_state(), path)

    def load(self, path: str):
        checkpoint = torch.load(path, map_location="cpu")
        if isinstance(checkpoint, dict) and "online_net" in checkpoint:
            self.online_net.load_state_dict(checkpoint["online_net"])
            self.target_net.load_state_dict(checkpoint["target_net"])
            if "optimizer" in checkpoint:
                self.optimizer.load_state_dict(checkpoint["optimizer"])
            if "step_count" in checkpoint:
                self.step_count = checkpoint["step_count"]
        else:
            self.online_net.load_state_dict(checkpoint)
            self.sync_target_network()
        self.target_net.eval()
