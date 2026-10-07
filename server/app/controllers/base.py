"""Base controller interface and contract for FlowSync traffic signal controllers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass(frozen=True)
class ControllerCapabilities:
    """Metadata declaring controller features and evaluation properties."""
    name: str
    version: str = "1.0.0"
    supports_uncertainty: bool = False
    supports_fallback: bool = False
    supports_training: bool = False
    uses_camera_observable_state_only: bool = True
    is_learning_based: bool = False
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "supports_uncertainty": self.supports_uncertainty,
            "supports_fallback": self.supports_fallback,
            "supports_training": self.supports_training,
            "uses_camera_observable_state_only": self.uses_camera_observable_state_only,
            "is_learning_based": self.is_learning_based,
            "description": self.description,
            # Frontend contract compatibility aliases
            "uses_uncertainty_estimation": self.supports_uncertainty,
            "supports_hysteretic_fallback": self.supports_fallback,
            "supports_safety_shield": True if self.supports_fallback or "flowsync" in self.name.lower() else False,
            "produces_q_values": self.is_learning_based,
            "handles_continuous_obs": True,
        }


@dataclass
class ControllerContext:
    """
    Context provided to controller at decision time.
    Separates environmental dynamics from hidden simulator truth.
    """
    timestep: int
    dt: float = 0.1
    current_phase: int = 0
    time_in_phase: float = 0.0
    color: str = "GREEN"  # "GREEN", "YELLOW", "RED"
    can_switch_phase: bool = True
    is_decision_step: bool = True
    valid_action_mask: Optional[np.ndarray] = None
    movement_queues: Optional[Dict[str, int]] = None
    outgoing_counts: Optional[Dict[str, int]] = None
    starvation_times: Optional[Dict[str, float]] = None
    raw_detections: Optional[List[Dict[str, Any]]] = None
    extra_telemetry: Dict[str, Any] = field(default_factory=dict)


class BaseController(ABC):
    """Abstract base class for all traffic signal controllers."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._last_diagnostics: Dict[str, Any] = {}
        self._step_count: int = 0

    @abstractmethod
    def act(self, observation: np.ndarray, context: ControllerContext) -> int:
        """
        Select traffic signal phase action (0-3).

        Args:
            observation: The normalized observation vector.
            context: Environment context (decision flags, masks, timers).

        Returns:
            Action integer representing selected phase index in [0, 3].
        """
        raise NotImplementedError

    @abstractmethod
    def reset(self, seed: Optional[int] = None) -> None:
        """Reset all internal state, timers, and metrics for a new episode."""
        self._last_diagnostics = {}
        self._step_count = 0

    @abstractmethod
    def get_capabilities(self) -> ControllerCapabilities:
        """Return capabilities and feature support metadata."""
        raise NotImplementedError

    def get_diagnostics(self) -> Dict[str, Any]:
        """Return diagnostic metrics from the most recent decision step."""
        return self._last_diagnostics.copy()

    def get_action(self, observation: np.ndarray, context: ControllerContext) -> int:
        """Alias for act() method."""
        return self.act(observation, context)

    def get_telemetry(self) -> Dict[str, Any]:
        """Alias for get_diagnostics() method."""
        return self.get_diagnostics()
