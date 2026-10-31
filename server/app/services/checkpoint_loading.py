"""Exact website checkpoint selection and staged version-compatible loading."""
import re

from ..rl.dqn_agent import DQNAgent


def parse_model_request(identifier: str, episode: int | None):
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("A model identifier is required")
    parts = identifier.strip().split(":")
    if (len(parts) > 2 or parts[0] in ("",".","..") or any(c in parts[0] for c in ("/","\\"))
            or any(ord(c) < 32 or ord(c) == 127 for c in parts[0])):
        raise ValueError("Invalid model identifier")
    if episode is not None and (type(episode) is not int or episode < 0):
        raise ValueError("Checkpoint slot must be a nonnegative integer")
    if len(parts) == 2:
        match = re.fullmatch(r"(?:checkpoint_)?(\d+)(?:\.pt)?",parts[1])
        if not match:
            raise ValueError("Invalid checkpoint suffix")
        suffix = int(match.group(1))
        if episode is not None and episode != suffix:
            raise ValueError("Conflicting checkpoint slots")
        episode = suffix
    return parts[0],episode


def select_checkpoint(paths, requested_slot=None):
    episodes = set()
    for path in paths:
        match = re.fullmatch(r"checkpoint_(\d+)\.pt",str(path).rsplit("/",1)[-1])
        if match:
            episodes.add(int(match.group(1)))
    if not episodes:
        raise FileNotFoundError("No checkpoints are available")
    if requested_slot is not None:
        if requested_slot not in episodes:
            raise FileNotFoundError(f"Requested checkpoint slot {requested_slot} is unavailable")
        return requested_slot
    return 0 if 0 in episodes else max(episodes)


def load_website_agent(checkpoint):
    """Construct before publication; file slot is not a trained episode count."""
    if not isinstance(checkpoint,dict) or type(checkpoint.get("episode")) is not int or checkpoint["episode"] < 0:
        raise ValueError("Checkpoint must record its actual nonnegative trained episode")
    agent = DQNAgent()
    agent.load_checkpoint_state(checkpoint)
    agent.online_net.eval()
    return agent,checkpoint["episode"]
