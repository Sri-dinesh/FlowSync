"""
d3qn.py — Dueling Double DQN (D3QN) Controller Baseline
=======================================================
Combines Dueling value-advantage decomposition with Double-DQN target
stabilization and demand action masking.
"""
from __future__ import annotations

import hashlib
import io
import time
from typing import Any, Dict, Optional
import numpy as np
import torch

from .base import BaseController, ControllerCapabilities, ControllerContext
from ..rl.dqn_agent import DQNAgent
from ..rl.dqn_network import DuelingDQNNetwork
from ..rl.hyperparams import HyperParams

HP = HyperParams()


class D3QNController(BaseController):
    """
    Dueling Double DQN traffic controller baseline.

    Args:
        agent: Optional pre-configured DQNAgent instance.
        checkpoint_path: Optional path to saved weights (.pt).
        deterministic: If True, operates strictly with epsilon=0.0.
    """

    def __init__(
        self,
        agent: Optional[DQNAgent] = None,
        checkpoint_path: Optional[str] = None,
        deterministic: bool = True,
    ) -> None:
        super().__init__(name="d3qn")
        self.agent = agent or DQNAgent()
        self.deterministic = deterministic
        self.epsilon: float = 0.0 if deterministic else HP.EPSILON_MIN

        if checkpoint_path is not None:
            self.load_checkpoint(checkpoint_path)

        self.agent.online_net.eval()
        self._checkpoint_hash: str = self._compute_checkpoint_hash()

    def reset(self, seed: Optional[int] = None) -> None:
        super().reset(seed=seed)
        self.agent.online_net.eval()
        if seed is not None:
            torch.manual_seed(seed)
            np.random.seed(seed)

    def load_checkpoint(self, path: str) -> None:
        """Load trained model weights."""
        checkpoint = torch.load(path, map_location=torch.device("cpu"), weights_only=True)
        if "online_net" in checkpoint:
            self.agent.online_net.load_state_dict(checkpoint["online_net"])
        else:
            self.agent.online_net.load_state_dict(checkpoint)
        self.agent.online_net.eval()
        self._checkpoint_hash = self._compute_checkpoint_hash()

    def _compute_checkpoint_hash(self) -> str:
        """Compute SHA-256 fingerprint of current network weights."""
        try:
            buf = io.BytesIO()
            torch.save(self.agent.online_net.state_dict(), buf)
            return hashlib.sha256(buf.getvalue()).hexdigest()[:16]
        except Exception:
            return "unknown_hash"

    def get_capabilities(self) -> ControllerCapabilities:
        return ControllerCapabilities(
            name="d3qn",
            version="1.0.0",
            supports_uncertainty=False,
            supports_fallback=False,
            supports_training=True,
            uses_camera_observable_state_only=True,
            is_learning_based=True,
            description="Dueling Double Deep Q-Network with demand action masking",
        )

    def act(self, observation: np.ndarray, context: ControllerContext) -> int:
        t0 = time.perf_counter()
        self._step_count += 1

        mask = context.valid_action_mask
        if mask is None:
            mask = np.ones(HP.ACTION_DIM, dtype=bool)

        valid_indices = np.where(mask)[0]
        if len(valid_indices) == 0:
            valid_indices = np.arange(HP.ACTION_DIM)
            mask = np.ones(HP.ACTION_DIM, dtype=bool)

        # Pad / truncate observation to match network expected input
        expected_dim = self.agent.online_net.feature_layer[0].in_features
        obs = observation
        if len(obs) < expected_dim:
            obs = np.pad(obs, (0, expected_dim - len(obs)), mode="constant")
        elif len(obs) > expected_dim:
            obs = obs[:expected_dim]

        state_tensor = torch.FloatTensor(obs).unsqueeze(0)
        mask_tensor = torch.BoolTensor(mask).unsqueeze(0)

        with torch.no_grad():
            q_values_tensor = self.agent.online_net(state_tensor, valid_action_mask=mask_tensor)
            q_values = q_values_tensor.squeeze(0).cpu().numpy()

        # Action selection
        eps = 0.0 if self.deterministic else self.epsilon
        if eps > 0.0 and np.random.random() < eps:
            action = int(np.random.choice(valid_indices))
        else:
            masked_q = np.copy(q_values)
            masked_q[~mask] = -1e9
            action = int(np.argmax(masked_q))

        inference_time_ms = (time.perf_counter() - t0) * 1000.0

        self._last_diagnostics = {
            "controller": "d3qn",
            "q_values": q_values.tolist(),
            "valid_action_mask": mask.tolist(),
            "selected_action": action,
            "inference_time_ms": inference_time_ms,
            "checkpoint_hash": self._checkpoint_hash,
            "deterministic": self.deterministic,
        }
        return action
