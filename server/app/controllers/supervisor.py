"""
supervisor.py — Controller Authority Supervisor with Hysteretic Fallback
=========================================================================
Task 1A.5 & Task C4: Manages authority transfer between RL policy and
deterministic Max-Pressure fallback based on online perception uncertainty.

State Machine:
  RL_ACTIVE
     │
     │ Uncertainty U_t >= T_high
     ▼
  FALLBACK_ACTIVE (Max-Pressure)
     │
     │ Dwell time >= K_dwell AND U_t <= T_low for K_recover steps
     ▼
  RL_ACTIVE

Guarantees:
- Hysteresis (T_low < T_high) eliminates rapid chattering / controller thrashing.
- Minimum dwell time prevents partial-phase authority oscillation.
- All transfers are logged with entry/exit uncertainty and durations.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
import numpy as np


class ControlAuthority(Enum):
    RL_ACTIVE = "rl_active"
    FALLBACK_ACTIVE = "fallback_active"


@dataclass
class AuthorityTransition:
    step: int
    from_authority: str
    to_authority: str
    uncertainty_score: float
    reason: str
    dwell_duration_steps: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ControllerSupervisor:
    """
    Manages authority transfer between RL policy and fallback controller.

    Args:
        threshold_high: Uncertainty threshold triggering switch to fallback (default 0.45).
        threshold_low: Uncertainty threshold permitting return to RL (default 0.25).
        min_dwell_steps: Minimum steps to remain in fallback before returning to RL (default 40 = 4.0s).
        recovery_window_steps: Consecutive steps uncertainty must stay below T_low (default 10 = 1.0s).
    """

    def __init__(
        self,
        threshold_high: float = 0.45,
        threshold_low: float = 0.25,
        min_dwell_steps: int = 40,
        recovery_window_steps: int = 10,
    ) -> None:
        self.threshold_high = threshold_high
        self.threshold_low = threshold_low
        self.min_dwell_steps = min_dwell_steps
        self.recovery_window_steps = recovery_window_steps

        self.authority: ControlAuthority = ControlAuthority.RL_ACTIVE
        self._steps_in_current_authority: int = 0
        self._consecutive_low_uncertainty_steps: int = 0
        self._transition_history: List[AuthorityTransition] = []

        # Aggregate metrics
        self.total_rl_steps: int = 0
        self.total_fallback_steps: int = 0
        self.total_switches: int = 0

    def reset(self) -> None:
        self.authority = ControlAuthority.RL_ACTIVE
        self._steps_in_current_authority = 0
        self._consecutive_low_uncertainty_steps = 0
        self._transition_history.clear()
        self.total_rl_steps = 0
        self.total_fallback_steps = 0
        self.total_switches = 0

    def update(self, uncertainty_score: float, step: int) -> ControlAuthority:
        """
        Evaluate uncertainty and update authority state machine.

        Returns:
            Current active ControlAuthority (RL_ACTIVE or FALLBACK_ACTIVE).
        """
        self._steps_in_current_authority += 1

        if self.authority == ControlAuthority.RL_ACTIVE:
            self.total_rl_steps += 1
            if uncertainty_score >= self.threshold_high:
                # Trigger fallback
                self.authority = ControlAuthority.FALLBACK_ACTIVE
                self.total_switches += 1
                trans = AuthorityTransition(
                    step=step,
                    from_authority=ControlAuthority.RL_ACTIVE.value,
                    to_authority=ControlAuthority.FALLBACK_ACTIVE.value,
                    uncertainty_score=uncertainty_score,
                    reason=f"uncertainty_exceeded_threshold_{uncertainty_score:.3f}>={self.threshold_high:.3f}",
                    dwell_duration_steps=self._steps_in_current_authority,
                )
                self._transition_history.append(trans)
                self._steps_in_current_authority = 0
                self._consecutive_low_uncertainty_steps = 0

        elif self.authority == ControlAuthority.FALLBACK_ACTIVE:
            self.total_fallback_steps += 1

            # Check recovery conditions
            if uncertainty_score <= self.threshold_low:
                self._consecutive_low_uncertainty_steps += 1
            else:
                self._consecutive_low_uncertainty_steps = 0

            can_return = (
                self._steps_in_current_authority >= self.min_dwell_steps
                and self._consecutive_low_uncertainty_steps >= self.recovery_window_steps
            )

            if can_return:
                # Return authority to RL
                self.authority = ControlAuthority.RL_ACTIVE
                self.total_switches += 1
                trans = AuthorityTransition(
                    step=step,
                    from_authority=ControlAuthority.FALLBACK_ACTIVE.value,
                    to_authority=ControlAuthority.RL_ACTIVE.value,
                    uncertainty_score=uncertainty_score,
                    reason=f"observation_stabilized_{uncertainty_score:.3f}<={self.threshold_low:.3f}",
                    dwell_duration_steps=self._steps_in_current_authority,
                )
                self._transition_history.append(trans)
                self._steps_in_current_authority = 0
                self._consecutive_low_uncertainty_steps = 0

        return self.authority

    def get_audit_summary(self) -> Dict[str, Any]:
        """Summary of supervisor operation."""
        total = max(1, self.total_rl_steps + self.total_fallback_steps)
        return {
            "current_authority": self.authority.value,
            "total_rl_steps": self.total_rl_steps,
            "total_fallback_steps": self.total_fallback_steps,
            "fallback_percentage": round((self.total_fallback_steps / total) * 100.0, 2),
            "total_authority_switches": self.total_switches,
            "transitions": [t.to_dict() for t in self._transition_history],
        }
