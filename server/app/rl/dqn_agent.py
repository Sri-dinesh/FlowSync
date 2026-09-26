"""
dqn_agent.py — Dueling Double DQN Agent with Masked Targets
=============================================================
Improvements in this version:
  - BUG-05 fix: train_step() uses action masks from replay buffer to:
      1. Mask advantage centering in the forward pass.
      2. Mask illegal actions from next_action selection in Double-DQN target.
         Previously: next_actions = online_net(next_states).argmax(1)  [unmasked]
         Corrected:  next_actions = argmax over valid actions only.
  - select_action(): accepts optional valid_action_mask to exclude illegal phases.
"""
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import logging
from typing import Optional, Dict
from app.rl.dqn_network import DuelingDQNNetwork
from app.rl.replay_buffer import PrioritizedReplayBuffer
from app.rl.hyperparams import HyperParams

logger = logging.getLogger(__name__)

HP = HyperParams()


class DQNAgent:
    """
    Dueling Double DQN with Prioritized Experience Replay and Action Masking.

    Architecture combines:
    - Dueling DQN: V(s) + A(s,a) decomposition with masked advantage centering (BUG-05)
    - Double DQN: online net selects action (masked), target net evaluates (reduces overestimation)
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
            eps=1e-8,       # Adam epsilon — slightly larger for stability
        )
        self.loss_fn = nn.SmoothL1Loss(reduction="none")  # per-sample loss for PER weighting
        self.replay_buffer = PrioritizedReplayBuffer(HP.REPLAY_BUFFER_SIZE)
        self.step_count = 0
        self.total_train_steps = 0  # BUG-B: persistent counter for diagnostics
        self.all_masked_fallback_count = 0  # A-03: audit all-masked fallback triggers
        self.latest_q_stats: Dict[str, float] = {}  # P-01/P-02/P-03: Q-value health metrics

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
            # BUG-05: pass mask for masked advantage centering
            q_values = self.online_net(state_tensor, valid_action_mask=mask_tensor)

        # Mask out invalid actions before argmax
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
        states, actions, rewards, next_states, dones, weights, indices, action_masks = batch

        # ── Current Q-values (online net) with masked centering ─────────────
        current_q_all = self.online_net(states, valid_action_mask=action_masks)
        current_q = current_q_all.gather(1, actions.unsqueeze(1)).squeeze(1)

        with torch.no_grad():
            # ── Double DQN: online net selects next action, masked by valid actions ──
            # Use action_masks as a proxy for next-state validity (conservative: same mask)
            next_q_online = self.online_net(next_states, valid_action_mask=action_masks)

            # BUG-05 CORRECTED: mask invalid actions before argmax
            next_q_masked = next_q_online.clone()
            # Set invalid action Q-values to -inf so they cannot be selected
            next_q_masked[~action_masks] = float("-inf")
            next_actions = next_q_masked.argmax(1)

            # ── Target net evaluates selected action ─────────────────────────
            next_q_target = self.target_net(next_states, valid_action_mask=action_masks)
            next_q = next_q_target.gather(1, next_actions.unsqueeze(1)).squeeze(1)

            # ── Bellman target ───────────────────────────────────────────────
            target_q = rewards + HP.GAMMA * next_q * (1 - dones)

        # ── Per-sample loss (needed for PER priority update) ─────────────────
        td_errors = (target_q - current_q).detach().cpu().numpy()
        per_sample_loss = self.loss_fn(current_q, target_q)

        # ── Weight loss by importance sampling weights (PER correction) ──────
        weighted_loss = (per_sample_loss * weights).mean()

        self.optimizer.zero_grad()
        weighted_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.online_net.parameters(), max_norm=10.0)
        self.optimizer.step()

        self.step_count += 1
        self.total_train_steps += 1  # BUG-B: track actual gradient updates

        # ── P-01/P-02/P-03: Q-value health monitoring ────────────────────────
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
        }

        # ── Update PER priorities with new TD errors ─────────────────────────
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
            "total_train_steps": self.total_train_steps,  # BUG-B: diagnostic
            "obs_version":       "v5_28dim_forecast",     # BUG-C fix: correct version
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
            # Legacy format — weights only
            self.online_net.load_state_dict(checkpoint)
            self.sync_target_network()
        self.target_net.eval()
