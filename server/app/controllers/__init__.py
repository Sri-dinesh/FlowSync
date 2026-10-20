"""Traffic signal controllers package exporting baseline and adaptive controllers."""
from __future__ import annotations

from typing import Any

from .base import BaseController, ControllerCapabilities, ControllerContext
from .fixed import FixedController
from .greedy import GreedyController
from .max_pressure import MaxPressureController
from .actuated import ActuatedController
from .dqn import DQNController
from .d3qn import D3QNController
from .safety_shield import SafetyShield, ShieldDecision
from .supervisor import ControllerSupervisor, ControlAuthority
from .flowsync_uq import FlowSyncUQController
from .physical_fsm import PhysicalSignalFSM, FSMDecision


CONTROLLER_REGISTRY = {
    "fixed": FixedController,
    "greedy": GreedyController,
    "max_pressure": MaxPressureController,
    "actuated": ActuatedController,
    "vat": ActuatedController,
    "plain_dqn": DQNController,
    "dqn": DQNController,
    "d3qn": D3QNController,
    "ai": D3QNController,
    "flowsync_uq": FlowSyncUQController,
}


def get_controller(name: str, **kwargs: Any) -> BaseController:
    """
    Factory function to instantiate a controller by name.

    Args:
        name: One of 'fixed', 'greedy', 'max_pressure', 'actuated'/'vat', 'dqn', 'd3qn'/'ai', 'flowsync_uq'.
        **kwargs: Additional parameters passed to controller constructor.

    Returns:
        Instance of BaseController.
    """
    if isinstance(name, dict):
        name = name.get("id") or name.get("name") or "flowsync_uq"
    key = str(name).lower().strip()
    if key in CONTROLLER_REGISTRY:
        return CONTROLLER_REGISTRY[key](**kwargs)
    raise ValueError(
        f"Unknown controller '{name}'. Available: {list(CONTROLLER_REGISTRY.keys())}"
    )


__all__ = [
    "BaseController",
    "ControllerCapabilities",
    "ControllerContext",
    "FixedController",
    "GreedyController",
    "MaxPressureController",
    "ActuatedController",
    "DQNController",
    "D3QNController",
    "SafetyShield",
    "ShieldDecision",
    "ControllerSupervisor",
    "ControlAuthority",
    "FlowSyncUQController",
    "PhysicalSignalFSM",
    "FSMDecision",
    "CONTROLLER_REGISTRY",
    "get_controller",
]
