"""Dueling Double DQN Agent with action masking and prioritized experience replay."""
import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import logging
import copy
import math
from numbers import Integral
from typing import Dict, Optional, Tuple
try:
    from .dqn_network import DuelingDQNNetwork
    from .replay_buffer import PrioritizedReplayBuffer
    from .hyperparams import HyperParams
    from .observations import OBSERVATION_DIMS
except (ImportError, ValueError):
    from app.rl.dqn_network import DuelingDQNNetwork
    from app.rl.replay_buffer import PrioritizedReplayBuffer
    from app.rl.hyperparams import HyperParams
    from app.rl.observations import OBSERVATION_DIMS

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

    def __init__(self, state_dim=HP.STATE_DIM, obs_version=HP.OBS_VERSION):
        self.state_dim = state_dim
        self.obs_version = obs_version
        self.reward_version = "v4_incremental_delay"
        self.online_net = DuelingDQNNetwork(state_dim, HP.ACTION_DIM)
        self.target_net = DuelingDQNNetwork(state_dim, HP.ACTION_DIM)
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
        self.demonstration_loss_weight = 0.10

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
        self.online_net = DuelingDQNNetwork(self.state_dim, HP.ACTION_DIM)
        self.target_net = DuelingDQNNetwork(self.state_dim, HP.ACTION_DIM)
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
        weighted_loss = td_loss + self.demonstration_loss_weight * demo_loss

        self.optimizer.zero_grad()
        weighted_loss.backward()
        gradient_norm = torch.nn.utils.clip_grad_norm_(self.online_net.parameters(), max_norm=10.0)
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
            # Keep scale diagnostics separate: shrinking PER weights can lower
            # weighted loss even while the same sampled prediction errors grow.
            "unweighted_td_loss": round(float(per_sample_loss.detach().mean().item()), 5),
            "pre_clip_gradient_norm": round(float(gradient_norm.item()), 5),
            "demo_margin_loss": round(float(demo_loss.item()), 5),
            "weighted_demo_loss": round(float(self.demonstration_loss_weight * demo_loss.item()), 5),
            "demo_sample_fraction": round(float(demo_flags.mean().item()), 5),
            "importance_weight_mean": round(float(weights.mean().item()), 5),
            "importance_weight_min": round(float(weights.min().item()), 5),
            "importance_weight_max": round(float(weights.max().item()), 5),
            "bootstrap_discount_mean": round(float(bootstrap_discounts.mean().item()), 5),
            "target_q_mean": round(float(target_q.mean().item()), 4),
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
            "obs_version":       self.obs_version,
            "reward_version":    self.reward_version,
            "demand_version":    "v2_total_lambda_with_upstream_backlog",
        }

    def save(self, path: str):
        torch.save(self.get_checkpoint_state(), path)

    def load_checkpoint_state(self, checkpoint: dict, *, allow_legacy_weights: bool = False) -> None:
        """Load compatible state atomically; tensor shape alone is not a schema.

        Structured artifacts must name this agent's observation and reward
        versions. Explicit legacy loading accepts weights under the caller's
        existing schema without claiming recovered training provenance. Missing
        target weights synchronize from online; absent saved counters reset to
        zero. Replay is not restored by this operation.
        """
        if not isinstance(checkpoint, dict):
            raise ValueError("Checkpoint must be a state dictionary")
        if OBSERVATION_DIMS.get(self.obs_version) != self.state_dim:
            raise ValueError("Agent observation version and input dimension differ")
        structured = "online_net" in checkpoint
        if structured:
            if checkpoint.get("obs_version") != self.obs_version:
                raise ValueError("Checkpoint observation version is incompatible with this agent")
            if checkpoint.get("reward_version") != self.reward_version:
                raise ValueError("Checkpoint reward version is incompatible with this agent")
            online_state = checkpoint["online_net"]
            target_state = checkpoint.get("target_net", online_state)
            counters = [checkpoint.get(name, 0) for name in ("step_count", "total_train_steps")]
            if any(isinstance(value, bool) or not isinstance(value, Integral) or value < 0 for value in counters):
                raise ValueError("Checkpoint counters must be nonnegative integers")
        else:
            if not allow_legacy_weights:
                raise ValueError("Unversioned weights require explicit allow_legacy_weights=True")
            online_state = target_state = checkpoint
            counters = [0, 0]

        # A joint deepcopy preserves the optimizer's references to the cloned
        # online parameters. Failed staging cannot partially replace a model.
        online, target, optimizer = copy.deepcopy((self.online_net, self.target_net, self.optimizer))
        try:
            online.load_state_dict(online_state, strict=True)
            target.load_state_dict(target_state, strict=True)
            if any(not torch.isfinite(value).all() for net in (online, target) for value in net.state_dict().values()):
                raise ValueError("Checkpoint network contains nonfinite values")
            if structured and "optimizer" in checkpoint:
                optimizer.load_state_dict(checkpoint["optimizer"])
                for parameter, state in optimizer.state.items():
                    for name, value in state.items():
                        if not torch.is_tensor(value):
                            continue
                        if not torch.isfinite(value).all():
                            raise ValueError("Checkpoint optimizer contains nonfinite values")
                        if name in ("exp_avg", "exp_avg_sq", "max_exp_avg_sq", "momentum_buffer") and value.shape != parameter.shape:
                            raise ValueError("Checkpoint optimizer tensor shape differs from its parameter")
                for group in optimizer.param_groups:
                    for name in ("lr", "eps", "weight_decay"):
                        if name in group and (not math.isfinite(group[name]) or group[name] < 0):
                            raise ValueError(f"Invalid checkpoint optimizer {name}")
                    if "betas" in group and (len(group["betas"]) != 2 or any(not math.isfinite(v) or not 0 <= v < 1 for v in group["betas"])):
                        raise ValueError("Invalid checkpoint optimizer betas")
            else:
                optimizer.state.clear()
        except (RuntimeError, TypeError, KeyError, IndexError, ValueError) as exc:
            raise ValueError(f"Incompatible checkpoint state: {exc}") from exc
        target.eval()
        self.online_net, self.target_net, self.optimizer = online, target, optimizer
        self.step_count, self.total_train_steps = map(int, counters)
        self.latest_q_stats = {}

    def load(self, path: str, *, allow_legacy_weights: bool = False) -> None:
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
        self.load_checkpoint_state(checkpoint, allow_legacy_weights=allow_legacy_weights)
