"""
physical_fsm.py — Mandatory Physical Signal State Machine (Fair Benchmark Layer)
================================================================================
Task 3 (P0): Ensures all evaluated traffic controllers pass through a mandatory,
uniform physical signal transition state machine (analogous to a NEMA TS2 MMU /
hardware signal cabinet).

This architecture guarantees:
1. No controller can execute conflicting green phases simultaneously.
2. Mandatory yellow clearance (3.0s) and all-red clearance (1.0s) are ALWAYS enforced.
3. Minimum green time (8.0s) is strictly enforced for physical lamp changes.
4. Proposed illegal actions (e.g. skipping yellow or switching early) are recorded
   as `proposed_violations`, while `executed_violations` are identically zero for
   all controllers operating with this physical layer.
5. FlowSync-UQ's additional safety layer (anti-starvation preemption, max-green ceiling,
   and uncertainty-triggered fallback) is cleanly separated and audited.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class FSMColor(Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


@dataclass
class FSMDecision:
    """Outcome of physical signal FSM validation for a single step."""
    proposed_phase: int
    executed_phase: int
    current_color: str
    time_in_phase: float
    is_proposed_violation: bool
    violation_reason: Optional[str] = None
    executed_violation: bool = False  # Always False under the physical FSM

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposed_phase": self.proposed_phase,
            "executed_phase": self.executed_phase,
            "current_color": self.current_color,
            "time_in_phase": self.time_in_phase,
            "is_proposed_violation": self.is_proposed_violation,
            "violation_reason": self.violation_reason,
            "executed_violation": self.executed_violation,
        }

    @property
    def executed_action(self) -> int:
        return self.executed_phase


class PhysicalSignalFSM:
    """
    Mandatory physical transition state machine.
    Simulates the physical signal cabinet hardware constraints.
    """

    def __init__(
        self,
        min_green: float = 8.0,
        yellow_duration: float = 3.0,
        all_red_duration: float = 1.0,
    ) -> None:
        self.min_green = min_green
        self.yellow_duration = yellow_duration
        self.all_red_duration = all_red_duration

        # Current physical state
        self.current_phase: int = 0
        self.color: FSMColor = FSMColor.GREEN
        self.time_in_phase: float = 0.0
        self.pending_phase: Optional[int] = None

        # Cumulative audit counters
        self.total_decisions: int = 0
        self.total_proposed_violations: int = 0
        self.total_executed_violations: int = 0
        self.violation_counts_by_reason: Dict[str, int] = {}

    def reset(self, initial_phase: int = 0) -> None:
        self.current_phase = initial_phase
        self.color = FSMColor.GREEN
        self.time_in_phase = 0.0
        self.pending_phase = None
        self.total_decisions = 0
        self.total_proposed_violations = 0
        self.total_executed_violations = 0
        self.violation_counts_by_reason.clear()

    def tick(self, dt: float = 1.0) -> None:
        """Advance physical signal timing by dt seconds."""
        self.time_in_phase += dt

        if self.color == FSMColor.YELLOW:
            if self.time_in_phase >= self.yellow_duration:
                self.color = FSMColor.RED
                self.time_in_phase = 0.0
        elif self.color == FSMColor.RED:
            if self.time_in_phase >= self.all_red_duration:
                if self.pending_phase is not None:
                    self.current_phase = self.pending_phase
                    self.pending_phase = None
                self.color = FSMColor.GREEN
                self.time_in_phase = 0.0

    def step(self, proposed_phase: int, dt: float = 1.0) -> FSMDecision:
        """
        Processes a controller's proposed phase.
        Enforces physical transitions:
          - If GREEN and proposed_phase != current_phase:
              - If time_in_phase < min_green: reject switch as proposed violation, keep GREEN.
              - If time_in_phase >= min_green: initiate YELLOW transition.
          - If YELLOW or RED (in clearance):
              - If proposed_phase != pending_phase (or trying to skip clearance):
                  record proposed violation, maintain clearance.
        """
        self.total_decisions += 1
        is_violation = False
        reason = None

        if self.color == FSMColor.GREEN:
            if proposed_phase != self.current_phase:
                if self.time_in_phase < self.min_green:
                    is_violation = True
                    reason = f"premature_switch_attempted (elapsed: {self.time_in_phase:.1f}s < min_green: {self.min_green:.1f}s)"
                    self.total_proposed_violations += 1
                    self.violation_counts_by_reason[reason] = self.violation_counts_by_reason.get(reason, 0) + 1
                    # Block switch physically: maintain green on current phase
                else:
                    # Valid physical switch initiated
                    self.pending_phase = proposed_phase
                    self.color = FSMColor.YELLOW
                    self.time_in_phase = 0.0
        else:
            # Currently in YELLOW or RED clearance
            if proposed_phase != self.current_phase and (self.pending_phase is not None and proposed_phase != self.pending_phase):
                is_violation = True
                reason = f"clearance_override_attempted (color: {self.color.value}, time: {self.time_in_phase:.1f}s)"
                self.total_proposed_violations += 1
                self.violation_counts_by_reason[reason] = self.violation_counts_by_reason.get(reason, 0) + 1

        decision = FSMDecision(
            proposed_phase=proposed_phase,
            executed_phase=self.current_phase if self.color != FSMColor.RED else (self.pending_phase if self.pending_phase is not None else self.current_phase),
            current_color=self.color.value,
            time_in_phase=self.time_in_phase,
            is_proposed_violation=is_violation,
            violation_reason=reason,
            executed_violation=False,  # Physical FSM never executes an illegal transition
        )

        # Advance time by dt
        self.tick(dt=dt)
        return decision
