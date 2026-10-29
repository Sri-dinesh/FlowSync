"""Research-only masked PPO actor; inherited D3QN scores become policy logits.

PPO: Schulman et al. (2017), https://arxiv.org/abs/1707.06347.
This adapter is deliberately absent from the application's controller registry.
"""
from dataclasses import dataclass
import hashlib
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.distributions import Categorical

from server.app.controllers.base import BaseController, ControllerCapabilities
from server.app.rl.dqn_network import DuelingDQNNetwork
from server.app.rl.observations import OBSERVED_VERSION, encode_policy_observation

VERSION = "masked_smdp_ppo_v1"
REWARD_VERSION = "v5_single_switch_delay"
DECISION_TICKS = 20


class ActorCritic(nn.Module):
    def __init__(self):
        super().__init__()
        self.actor = DuelingDQNNetwork(36, 4)
        # Retain the complete computation for exact initial greedy parity. This
        # common scalar cancels from categorical probabilities; it is not a critic.
        self.actor.value_stream.requires_grad_(False)
        self.critic = nn.Sequential(nn.Linear(36, 64), nn.Tanh(), nn.Linear(64, 64),
                                    nn.Tanh(), nn.Linear(64, 1))
        nn.init.zeros_(self.critic[-1].weight)
        nn.init.zeros_(self.critic[-1].bias)

    def distribution(self, states, masks):
        if states.ndim != 2 or states.shape[1] != 36 or masks.shape != (len(states), 4):
            raise ValueError("PPO requires [batch,36] states and [batch,4] masks")
        if masks.dtype != torch.bool or not masks.any(dim=1).all():
            raise ValueError("PPO requires a nonempty boolean action mask")
        logits = self.actor(states, masks)
        if not torch.isfinite(logits).all():
            raise ValueError("Nonfinite policy logits")
        return Categorical(logits=logits.masked_fill(~masks, -torch.inf))

    def values(self, states):
        return self.critic(states).squeeze(-1)

    @classmethod
    def from_parent(cls, path):
        payload = torch.load(path, map_location="cpu", weights_only=True)
        if payload.get("obs_version") != OBSERVED_VERSION or payload.get("reward_version") != REWARD_VERSION:
            raise ValueError("PPO warm start requires the frozen v7/v5 parent")
        model = cls()
        model.actor.load_state_dict(payload["online_net"], strict=True)
        return model


def save_checkpoint(path, model, metadata):
    payload = dict(schema_version=VERSION, obs_version=OBSERVED_VERSION,
                   reward_version=REWARD_VERSION, state_dict=model.state_dict(), metadata=metadata)
    torch.save(payload, path)


@dataclass(frozen=True)
class PolicyCapabilities(ControllerCapabilities):
    def to_dict(self):
        return {**super().to_dict(), "produces_q_values": False}


class PPOController(BaseController):
    """Greedy evaluation of an explicit PPO checkpoint at the trained cadence."""
    def __init__(self, path):
        super().__init__("ppo")
        self.path = Path(path).resolve()
        payload = torch.load(self.path, map_location="cpu", weights_only=True)
        if (payload.get("schema_version") != VERSION or payload.get("obs_version") != OBSERVED_VERSION
                or payload.get("reward_version") != REWARD_VERSION):
            raise ValueError("Incompatible PPO checkpoint")
        self.model = ActorCritic()
        self.model.load_state_dict(payload["state_dict"], strict=True)
        self.model.eval()
        self.metadata = payload["metadata"]
        self.hash = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.next_decision = self.held_action = 0

    def reset(self, seed=None):
        super().reset(seed)
        self.next_decision = self.held_action = 0

    def get_capabilities(self):
        return PolicyCapabilities(name=self.name, is_learning_based=True, supports_training=True,
                                  description="Masked PPO policy; inherited dueling actor and independent critic")

    def act(self, observation, context):
        self._step_count += 1
        if not context.is_decision_step:
            return context.current_phase
        if context.timestep < self.next_decision:
            return self.held_action
        state = torch.as_tensor(encode_policy_observation(observation, context, OBSERVED_VERSION)).unsqueeze(0)
        mask = torch.as_tensor(context.valid_action_mask, dtype=torch.bool).unsqueeze(0)
        with torch.no_grad():
            policy = self.model.distribution(state, mask)
            action = int(policy.logits.argmax(1))
            value = float(self.model.values(state)[0])
        self.held_action = action
        self.next_decision = context.timestep + max(1, round(2. / context.dt))
        self._last_diagnostics = dict(controller=self.name, selected_action=action,
            policy_probabilities=policy.probs[0].tolist(), value_estimate=value,
            valid_action_mask=mask[0].tolist())
        return action

    def get_diagnostics(self):
        return {**super().get_diagnostics(), "checkpoint_loaded": True, "checkpoint_hash": self.hash,
                "checkpoint_path": str(self.path), "checkpoint_metadata": self.metadata, "deterministic": True}
