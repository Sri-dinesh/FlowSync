"""
flowsync_uq.py — FlowSync-UQ Uncertainty-Aware Safe Fallback Controller
========================================================================
Core Proposed Method (Task C1, C2, C3, C4):
Integrates:
1. Dueling Double DQN (D3QN) learned control policy.
2. Online Perception Uncertainty Estimator (multi-feature reliability).
3. Max-Pressure deterministic adaptive fallback controller.
4. Hysteretic Authority Supervisor with minimum dwell times.
5. Independent Formal SafetyShield enforcing transition and clearance invariants.

Operational Pipeline:
  Observation s_t
       ↓
  Uncertainty Engine: U_t = Estimator(s_t)
       ↓
  Supervisor Decision:
     if U_t >= T_high: Authority = FALLBACK (Max-Pressure)
     elif U_t <= T_low & dwell_met: Authority = RL (D3QN)
       ↓
  Candidate Action Proposal
       ↓
  SafetyShield: Enforce min-green, clearance, max-green, starvation
       ↓
  Executed Safe Action a_t
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
import numpy as np

from .base import BaseController, ControllerCapabilities, ControllerContext
from .d3qn import D3QNController
from .max_pressure import MaxPressureController
from .safety_shield import SafetyShield, ShieldDecision
from .supervisor import ControllerSupervisor, ControlAuthority
from research.uncertainty.estimator import PerceptionUncertaintyEstimator, UncertaintyScore


class FlowSyncUQController(BaseController):
    """
    Uncertainty-Aware Safe Fallback Controller for Vision-Based Traffic Signals.

    Args:
        d3qn_controller: Pre-configured D3QN controller instance.
        fallback_controller: Deterministic fallback controller (default: MaxPressureController).
        uncertainty_estimator: Online multi-feature uncertainty estimator.
        safety_shield: Formal safety invariant enforcement layer.
        supervisor: Authority transfer state machine.
    """

    def __init__(
        self,
        d3qn_controller: Optional[D3QNController] = None,
        fallback_controller: Optional[BaseController] = None,
        uncertainty_estimator: Optional[PerceptionUncertaintyEstimator] = None,
        safety_shield: Optional[SafetyShield] = None,
        supervisor: Optional[ControllerSupervisor] = None,
        threshold_high: float = 0.45,
        threshold_low: float = 0.25,
        min_dwell_steps: int = 40,
        uncertainty_threshold: Optional[float] = None,
        enable_shield: bool = True,
        fallback_controller_name: Optional[str] = None,
    ) -> None:
        super().__init__(name="flowsync_uq")

        if uncertainty_threshold is not None:
            threshold_high = uncertainty_threshold
            threshold_low = uncertainty_threshold * 0.6

        self.threshold_high = threshold_high
        self.threshold_low = threshold_low
        self.uncertainty_threshold = threshold_high
        self.enable_shield = enable_shield
        self.fallback_controller_name = fallback_controller_name or "max_pressure"

        self.d3qn = d3qn_controller or D3QNController(deterministic=True)

        if fallback_controller is not None:
            self.fallback = fallback_controller
        elif fallback_controller_name is not None:
            from . import get_controller
            self.fallback = get_controller(fallback_controller_name)
        else:
            self.fallback = MaxPressureController()

        self.uncertainty_estimator = uncertainty_estimator or PerceptionUncertaintyEstimator(
            threshold_high=threshold_high,
            threshold_low=threshold_low,
        )
        self.safety_shield = safety_shield or SafetyShield()
        self.supervisor = supervisor or ControllerSupervisor(
            threshold_high=threshold_high,
            threshold_low=threshold_low,
            min_dwell_steps=min_dwell_steps,
        )

        self._last_uncertainty: Optional[UncertaintyScore] = None
        self._last_shield_decision: Optional[ShieldDecision] = None
        self._last_authority: ControlAuthority = ControlAuthority.RL_ACTIVE

    def reset(self, seed: Optional[int] = None) -> None:
        super().reset(seed=seed)
        self.d3qn.reset(seed=seed)
        self.fallback.reset(seed=seed)
        self.uncertainty_estimator.reset()
        self.safety_shield.reset()
        self.supervisor.reset()
        self._last_uncertainty = None
        self._last_shield_decision = None
        self._last_authority = ControlAuthority.RL_ACTIVE

    def get_capabilities(self) -> ControllerCapabilities:
        return ControllerCapabilities(
            name="flowsync_uq",
            version="1.0.0",
            supports_uncertainty=True,
            supports_fallback=True,
            supports_training=True,
            uses_camera_observable_state_only=True,
            is_learning_based=True,
            description="Uncertainty-Aware Safe Fallback D3QN Controller with Max-Pressure Backup",
        )

    def act(self, observation: np.ndarray, context: ControllerContext) -> int:
        t0 = time.perf_counter()
        self._step_count += 1

        # 1. Compute perception uncertainty
        forecast_feats = observation[20:28] if len(observation) >= 28 else None
        obs_age = float(context.extra_telemetry.get("observation_age_ms", 0.0))
        frame_drop = bool(context.extra_telemetry.get("frame_dropped", False))
        confidences = context.extra_telemetry.get("detection_confidences", None)

        u_score = self.uncertainty_estimator.compute(
            observed_queues=observation[:12],
            forecast_features=forecast_feats,
            detection_confidences=confidences,
            observation_age_ms=obs_age,
            frame_dropped=frame_drop,
        )
        self._last_uncertainty = u_score

        # 2. Update supervisor state machine
        authority = self.supervisor.update(u_score.score, step=self._step_count)
        self._last_authority = authority

        # 3. Consult designated controller
        if authority == ControlAuthority.RL_ACTIVE:
            proposed_action = self.d3qn.act(observation, context)
            q_values = self.d3qn.get_diagnostics().get("q_values", [])
            active_controller = "d3qn"
        else:
            proposed_action = self.fallback.act(observation, context)
            q_values = []
            active_controller = "max_pressure_fallback"

        # 4. Enforce Safety Shield invariants (if enabled)
        if self.enable_shield and self.safety_shield is not None:
            shield_decision = self.safety_shield.filter_action(
                proposed_action=proposed_action,
                current_phase=context.current_phase,
                time_in_phase=context.time_in_phase,
                color=context.color,
                valid_action_mask=context.valid_action_mask,
                starvation_timers={i: context.starvation_times.get(d, 0.0) for i, d in enumerate(["north", "east", "south", "west"])} if context.starvation_times else None,
            )
        else:
            shield_decision = ShieldDecision(
                proposed_action=proposed_action,
                executed_action=proposed_action,
                was_overridden=False,
                override_reason="none_shield_bypassed",
            )
        self._last_shield_decision = shield_decision
        executed_action = shield_decision.executed_action

        inference_time_ms = (time.perf_counter() - t0) * 1000.0

        # 5. Record complete diagnostics
        self._last_diagnostics = {
            "controller": "flowsync_uq",
            "active_controller": active_controller,
            "authority": authority.value,
            "uncertainty_score": round(u_score.score, 4),
            "uncertainty_features": u_score.features.to_dict(),
            "proposed_action": proposed_action,
            "executed_action": executed_action,
            "was_overridden": shield_decision.was_overridden,
            "override_reason": shield_decision.override_reason,
            "q_values": q_values,
            "inference_time_ms": round(inference_time_ms, 3),
            "checkpoint_hash": self.d3qn._checkpoint_hash,
        }

        return executed_action
