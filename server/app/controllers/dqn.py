"""
dqn.py — Plain Deep Q-Network (DQN) Signal Controller Baseline (Mnih et al. 2015)
==================================================================================
Standard deep reinforcement learning baseline without dueling streams,
double-DQN target stabilization, or prioritized replay.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional
import numpy as np
import torch

from .base import BaseController, ControllerCapabilities, ControllerContext
from ..rl.dqn_network import PlainDQNNetwork
from ..rl.hyperparams import HyperParams

logger = logging.getLogger(__name__)
HP = HyperParams()


class DQNController(BaseController):
    """
    Standard DQN traffic controller baseline.
    """

    def __init__(
        self,
        network: Optional[PlainDQNNetwork] = None,
        state_dim: int = HP.STATE_DIM,
        action_dim: int = HP.ACTION_DIM,
    ) -> None:
        super().__init__(name="plain_dqn")
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.network = network or PlainDQNNetwork(state_dim=state_dim, action_dim=action_dim)
        self.network.eval()
        self.epsilon: float = 0.0

    def reset(self, seed: Optional[int] = None) -> None:
        super().reset(seed=seed)
        self.network.eval()

    def get_capabilities(self) -> ControllerCapabilities:
        return ControllerCapabilities(
            name="plain_dqn",
            version="1.0.0",
            supports_uncertainty=False,
            supports_fallback=False,
            supports_training=True,
            uses_camera_observable_state_only=True,
            is_learning_based=True,
            description="Standard DQN baseline without dueling streams or double-DQN updates",
        )

    def act(self, observation: np.ndarray, context: ControllerContext) -> int:
        self._step_count += 1

        mask = context.valid_action_mask
        if mask is None:
            mask = np.ones(self.action_dim, dtype=bool)

        valid_indices = np.where(mask)[0]
        if len(valid_indices) == 0:
            valid_indices = np.arange(self.action_dim)
            mask = np.ones(self.action_dim, dtype=bool)

        # Pad or truncate observation if needed
        obs = observation
        if len(obs) < self.state_dim:
            obs = np.pad(obs, (0, self.state_dim - len(obs)), mode="constant")
        elif len(obs) > self.state_dim:
            obs = obs[:self.state_dim]

        state_tensor = torch.FloatTensor(obs).unsqueeze(0)

        with torch.no_grad():
            q_values_tensor = self.network(state_tensor)
            q_values = q_values_tensor.squeeze(0).cpu().numpy()

        masked_q = np.copy(q_values)
        masked_q[~mask] = -1e9

        selected_action = int(np.argmax(masked_q))

        self._last_diagnostics = {
            "controller": "plain_dqn",
            "q_values": q_values.tolist(),
            "valid_action_mask": mask.tolist(),
            "selected_action": selected_action,
        }
        return selected_action
