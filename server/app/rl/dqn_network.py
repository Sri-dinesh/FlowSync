"""
dqn_network.py — Dueling DQN Architecture with Masked Advantage Centering
==========================================================================
Improvements in this version:
  - BUG-05 fix: DuelingDQNNetwork.forward() now accepts an optional valid_action_mask.
    When provided, advantage centering uses mean only over VALID actions (not all 4).
    This prevents invalid/empty phases from biasing the Q-value baseline estimate.

  Corrected formula:
    Q(s,a) = V(s) + A(s,a) - mean_{a' ∈ valid(s)} A(s, a')

  Previously used:
    Q(s,a) = V(s) + A(s,a) - mean_{all 4 actions} A(s, a')   ← BUG-05
"""
import torch
import torch.nn as nn
from typing import Optional
from app.rl.hyperparams import HyperParams

HP = HyperParams()


class DuelingDQNNetwork(nn.Module):
    """
    Dueling DQN Architecture with valid-action masked advantage centering.
    Based on: Wang et al. 2016, FPA-DQN 2025, 3DQN 2025.

    Splits Q(s,a) into:
      V(s)    — state value stream (how good is this state)
      A(s,a)  — advantage stream (how much better is each action)
      Q(s,a)  = V(s) + A(s,a) - mean_{a' ∈ valid} A(s,a')   ← BUG-05 corrected

    Args:
        state_dim: Input observation dimension (default 20, will be 28 post-Task 4.2).
        action_dim: Number of actions (4 signal phases).
    """

    def __init__(self, state_dim: int = 20, action_dim: int = 4):
        super().__init__()
        self.action_dim = action_dim

        # Shared feature extraction backbone
        self.feature_layer = nn.Sequential(
            nn.Linear(state_dim, 256),
            nn.LayerNorm(256),
            nn.ReLU(),
            nn.Linear(256, 256),
            nn.LayerNorm(256),
            nn.ReLU(),
        )

        # Value stream V(s) — single scalar
        self.value_stream = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 1),   # outputs V(s)
        )

        # Advantage stream A(s,a) — one per action
        self.advantage_stream = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, action_dim),  # outputs A(s,a) for each action
        )

        self._init_weights()

    def _init_weights(self):
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.kaiming_uniform_(module.weight, nonlinearity="relu")
                nn.init.zeros_(module.bias)

    def forward(
        self,
        x: torch.Tensor,
        valid_action_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Observation tensor [batch, state_dim].
            valid_action_mask: Optional bool tensor [batch, action_dim].
                When provided, advantage centering is computed only over valid actions.
                If None, falls back to mean over all actions (backward-compatible).

        Returns:
            Q-values tensor [batch, action_dim].
        """
        features = self.feature_layer(x)

        value = self.value_stream(features)        # (batch, 1)
        advantage = self.advantage_stream(features)  # (batch, action_dim)

        if valid_action_mask is not None:
            # BUG-05 CORRECTED: compute mean only over valid action dimensions
            # valid_action_mask: True for valid actions, False for invalid
            # Shape: (batch, action_dim) bool
            float_mask = valid_action_mask.float()  # 1.0 = valid, 0.0 = invalid

            # Masked advantage sum, divide by number of valid actions per sample
            n_valid = float_mask.sum(dim=1, keepdim=True).clamp(min=1.0)
            masked_advantage_mean = (advantage * float_mask).sum(dim=1, keepdim=True) / n_valid
            q_values = value + advantage - masked_advantage_mean
        else:
            # Unmasked fallback (backward compat; used when mask unavailable)
            q_values = value + advantage - advantage.mean(dim=1, keepdim=True)

        return q_values  # (batch, action_dim)
