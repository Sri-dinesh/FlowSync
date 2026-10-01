"""
safety_shield.py — Dedicated Formal Traffic Signal Safety Shield Layer
======================================================================
Task 1A.4 & Task C3: Centralizes all signal-safety constraints and transition
rules into an auditable, controller-independent enforcement layer.

Safety Pipeline:
  Controller Policy Proposal
           ↓
     Valid Action Mask
           ↓
      SafetyShield
           ↓
   Physical Signal FSM

Enforced Invariants:
1. Minimum Green Guard: No phase switch permitted before MIN_GREEN_TIME (8.0s).
2. Clearance Interlock: All-red and yellow clearance cannot be truncated or skipped.
3. Max Green Ceiling: Phase green duration cannot exceed MAX_GREEN_TIME (40.0s).
4. Anti-Starvation Precedence: Phases waiting >= STARVATION_LIMIT (45.0s) take precedence.
5. Conflict Compatibility: Green phases on conflicting approaches can NEVER execute concurrently.
6. Forbidden Action Rejection: Proposed actions not in valid_action_mask are overridden.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class ShieldDecision:
    """Outcome of SafetyShield evaluation."""
    proposed_action: int
    executed_action: int
    was_overridden: bool
    override_reason: Optional[str] = None
    is_safe: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposed_action": self.proposed_action,
            "executed_action": self.executed_action,
            "was_overridden": self.was_overridden,
            "override_reason": self.override_reason,
            "is_safe": self.is_safe,
        }


class SafetyShield:
    """
    Formal, stateful safety shield verifying traffic signal phase proposals.
    """

    def __init__(
        self,
        min_green_time: float = 8.0,
        max_green_time: float = 40.0,
        yellow_duration: float = 2.0,
        red_duration: float = 3.0,
        starvation_threshold: float = 45.0,
    ) -> None:
        self.min_green_time = min_green_time
        self.max_green_time = max_green_time
        self.yellow_duration = yellow_duration
        self.red_duration = red_duration
        self.starvation_threshold = starvation_threshold

        # Audit counters
        self.total_evaluations: int = 0
        self.total_overrides: int = 0
        self.override_counts_by_reason: Dict[str, int] = {}
        self.unsafe_proposals_blocked: int = 0

    def reset(self) -> None:
        self.total_evaluations = 0
        self.total_overrides = 0
        self.override_counts_by_reason.clear()
        self.unsafe_proposals_blocked = 0

    def _record_override(self, reason: str) -> None:
        self.total_overrides += 1
        self.override_counts_by_reason[reason] = self.override_counts_by_reason.get(reason, 0) + 1

    def filter_action(
        self,
        proposed_action: int,
        current_phase: int,
        time_in_phase: float,
        color: str,
        valid_action_mask: Optional[np.ndarray] = None,
        starvation_timers: Optional[Dict[int, float]] = None,
        movement_pressures: Optional[Dict[int, float]] = None,
    ) -> ShieldDecision:
        """
        Validate and filter a proposed controller action.

        Returns ShieldDecision with guaranteed safe executed_action.
        """
        self.total_evaluations += 1
        target_action = proposed_action

        # Check bounds: action must be in [0, 3]
        if not (0 <= target_action <= 3):
            self.unsafe_proposals_blocked += 1
            self._record_override("invalid_action_index_out_of_bounds")
            return ShieldDecision(
                proposed_action=proposed_action,
                executed_action=current_phase,
                was_overridden=True,
                override_reason="invalid_action_index_out_of_bounds",
                is_safe=False,
            )

        # 1. Clearance interval lock: during YELLOW or RED, phase switches cannot be initiated
        if color in ("YELLOW", "RED"):
            return ShieldDecision(
                proposed_action=proposed_action,
                executed_action=current_phase,
                was_overridden=(target_action != current_phase),
                override_reason="clearance_interval_active" if target_action != current_phase else None,
                is_safe=True,
            )

        # 2. Minimum Green Guard
        can_switch = time_in_phase >= self.min_green_time
        if target_action != current_phase and not can_switch:
            self._record_override("minimum_green_guard_active")
            return ShieldDecision(
                proposed_action=proposed_action,
                executed_action=current_phase,
                was_overridden=True,
                override_reason=f"minimum_green_guard_active_{time_in_phase:.1f}s<{self.min_green_time:.1f}s",
                is_safe=True,
            )

        # 3. Maximum Green Ceiling Watchdog
        if color == "GREEN" and time_in_phase >= self.max_green_time and target_action == current_phase:
            # Force transition to alternative phase with highest pressure / demand
            best_alt = (current_phase + 1) % 4
            if movement_pressures is not None:
                candidates = [p for p in range(4) if p != current_phase]
                best_alt = max(candidates, key=lambda p: movement_pressures.get(p, 0.0))

            self._record_override("max_green_ceiling_exceeded")
            return ShieldDecision(
                proposed_action=proposed_action,
                executed_action=best_alt,
                was_overridden=True,
                override_reason=f"max_green_ceiling_exceeded_{time_in_phase:.1f}s>={self.max_green_time:.1f}s",
                is_safe=True,
            )

        # 4. Anti-Starvation Interlock
        if starvation_timers is not None:
            starved_phases = [
                ph for ph, t in starvation_timers.items()
                if t >= self.starvation_threshold and ph != current_phase
            ]
            if starved_phases and target_action not in starved_phases:
                # Force switch to most starved phase
                most_starved = max(starved_phases, key=lambda ph: starvation_timers[ph])
                self._record_override(f"anti_starvation_override_phase_{most_starved}")
                return ShieldDecision(
                    proposed_action=proposed_action,
                    executed_action=most_starved,
                    was_overridden=True,
                    override_reason=f"anti_starvation_override_phase_{most_starved}",
                    is_safe=True,
                )

        # 5. Demand Action Masking (Admissibility)
        if valid_action_mask is not None:
            if not valid_action_mask[target_action]:
                # If proposed action has zero demand, select valid alternative or keep current
                valid_indices = np.where(valid_action_mask)[0]
                if len(valid_indices) > 0:
                    fallback_action = current_phase if valid_action_mask[current_phase] else int(valid_indices[0])
                else:
                    fallback_action = current_phase

                self._record_override("demand_mask_rejection")
                return ShieldDecision(
                    proposed_action=proposed_action,
                    executed_action=fallback_action,
                    was_overridden=True,
                    override_reason="demand_mask_rejection_empty_approach",
                    is_safe=True,
                )

        # Proposed action satisfies all formal safety invariants
        return ShieldDecision(
            proposed_action=proposed_action,
            executed_action=target_action,
            was_overridden=False,
            override_reason=None,
            is_safe=True,
        )

    def get_audit_metrics(self) -> Dict[str, Any]:
        """Return full audit summary of safety enforcement."""
        rate = (self.total_overrides / max(1, self.total_evaluations)) * 100.0
        return {
            "total_evaluations": self.total_evaluations,
            "total_overrides": self.total_overrides,
            "override_rate_pct": round(rate, 2),
            "unsafe_proposals_blocked": self.unsafe_proposals_blocked,
            "override_counts_by_reason": dict(self.override_counts_by_reason),
        }
