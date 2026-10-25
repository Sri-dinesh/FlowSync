"""Availability and provenance contract for the interactive research runtime."""
from ..controllers import get_controller

LIVE_CONTROLLERS = ("fixed", "greedy", "actuated", "max_pressure")
LEARNED_CONTROLLERS = ("dqn", "d3qn", "flowsync_uq")
LEARNED_UNAVAILABLE = (
    "Live learned research control requires checkpoint loading and the matching "
    "observed-input runtime. This session does not implement that contract. "
    "Use checkpoint-explicit headless evaluation or replay a recorded run."
)


def runtime_contract():
    return {
        "runtime": "interactive_legacy",
        "simulation_only": True,
        "audited_headless_parity": False,
        "learned_checkpoint_loading": False,
        "available_controllers": list(LIVE_CONTROLLERS),
        "unavailable_reason": LEARNED_UNAVAILABLE,
        "documentation": "CONTENT.md",
    }


def live_controller(name):
    if name not in LIVE_CONTROLLERS:
        if name in (*LEARNED_CONTROLLERS, "ai", "plain_dqn"):
            raise ValueError(LEARNED_UNAVAILABLE)
        raise ValueError(f"Unknown live controller: {name}")
    return get_controller(name)
