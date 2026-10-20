"""Explicit v7-to-v8 weight expansion for a matched research pilot only."""
import torch

from server.app.rl.observations import OBSERVED_VERSION, TEMPORAL_VERSIONS


def initialize_parent(agent, checkpoint, expand_v7=False):
    version = checkpoint.get("obs_version")
    weights = checkpoint["online_net"]
    if expand_v7:
        if version != OBSERVED_VERSION or agent.obs_version not in TEMPORAL_VERSIONS:
            raise ValueError("Expansion requires a v7 parent and an explicit v8 observation version")
        weights = {key: value.clone() for key, value in weights.items()}
        key = "feature_layer.0.weight"
        source = weights[key]
        target = agent.online_net.state_dict()[key]
        if source.shape != (target.shape[0], 36) or target.shape[1] != 64:
            raise ValueError("Unexpected parent input-layer shape")
        expanded = torch.zeros_like(target)
        expanded[:, :36] = source
        weights[key] = expanded
    elif version != agent.obs_version:
        raise ValueError("Parent checkpoint observation version must match the requested version")
    if any(not torch.isfinite(value).all() for value in weights.values()):
        raise ValueError("Parent checkpoint contains non-finite weights")
    agent.online_net.load_state_dict(weights, strict=True)
    agent.sync_target_network()
