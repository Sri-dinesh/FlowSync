import torch
import torch.nn as nn
from app.rl.hyperparams import HyperParams

HP = HyperParams()

class DuelingDQNNetwork(nn.Module):
    """
    Dueling DQN Architecture.
    Based on: Wang et al. 2016, FPA-DQN 2025, 3DQN 2025.

    Splits Q(s,a) into:
      V(s)    — state value stream (how good is this state)
      A(s,a)  — advantage stream (how much better is each action)
      Q(s,a)  = V(s) + A(s,a) - mean(A(s,a))
    """
    def __init__(self, state_dim: int = 20, action_dim: int = 4):
        super().__init__()

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
            nn.Linear(128, 1)   # outputs V(s)
        )

        # Advantage stream A(s,a) — one per action
        self.advantage_stream = nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, action_dim)  # outputs A(s,a) for each action
        )

        self._init_weights()

    def _init_weights(self):
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.kaiming_uniform_(module.weight, nonlinearity='relu')
                nn.init.zeros_(module.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        features = self.feature_layer(x)

        value = self.value_stream(features)           # (batch, 1)
        advantage = self.advantage_stream(features)   # (batch, 4)

        # Combine: Q(s,a) = V(s) + A(s,a) - mean_a[A(s,a')]
        # Subtracting mean stabilizes training (identifiability)
        q_values = value + advantage - advantage.mean(dim=1, keepdim=True)

        return q_values  # (batch, 4)
