"""FlowSync-UQ uncertainty-aware safe fallback controller integrating D3QN, uncertainty estimation, and Max-Pressure."""
from __future__ import annotations

import time
from typing import Optional
import numpy as np

from .base import BaseController, ControllerCapabilities, ControllerContext
from .d3qn import D3QNController
from .max_pressure import MaxPressureController
from .safety_shield import SafetyShield, ShieldDecision
from .supervisor import ControllerSupervisor, ControlAuthority
from research.uncertainty.estimator import PerceptionUncertaintyEstimator, UncertaintyScore
from research.uncertainty.benefit_gate import FallbackBenefitGate, observable_features


class FlowSyncUQController(BaseController):
    """
    Uncertainty-Aware Safe Fallback Controller for Vision-Based Traffic Signals.

    Args:
        d3qn_controller: Pre-configured D3QN controller instance.
        fallback_controller: Deterministic fallback controller (default: MaxPressureController).
        uncertainty_estimator: Online multi-feature uncertainty estimator.
        safety_shield: Rule-based signal and phase-service guard.
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
        enable_fallback: bool = True,
        checkpoint_path: Optional[str] = None,
        max_observation_age_ms: float = 1000.0,
        calibration_path: Optional[str] = None,
        benefit_gate_path: Optional[str] = None,
    ) -> None:
        super().__init__(name="flowsync_uq")

        if uncertainty_threshold is not None:
            threshold_high = uncertainty_threshold
            threshold_low = uncertainty_threshold * 0.6

        self.threshold_high = threshold_high
        self.threshold_low = threshold_low
        self.uncertainty_threshold = threshold_high
        self.enable_shield = enable_shield
        self.enable_fallback = enable_fallback
        self.max_observation_age_ms = max_observation_age_ms
        self.fallback_controller_name = fallback_controller_name or "max_pressure"

        self.d3qn = d3qn_controller or D3QNController(deterministic=True, checkpoint_path=checkpoint_path)

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
            calibration_path=calibration_path,
        )
        if calibration_path is not None:
            threshold_high = self.uncertainty_estimator.threshold_high
            threshold_low = self.uncertainty_estimator.threshold_low
            self.threshold_high = self.uncertainty_threshold = threshold_high
            self.threshold_low = threshold_low
        self.safety_shield = safety_shield or SafetyShield()
        self.supervisor = supervisor or ControllerSupervisor(
            threshold_high=threshold_high,
            threshold_low=threshold_low,
            min_dwell_steps=min_dwell_steps,
        )

        self._last_uncertainty: Optional[UncertaintyScore] = None
        self._last_shield_decision: Optional[ShieldDecision] = None
        self._last_authority: ControlAuthority = ControlAuthority.RL_ACTIVE
        self.benefit_gate = FallbackBenefitGate(benefit_gate_path) if benefit_gate_path else None
        if self.benefit_gate is not None:
            if self.benefit_gate.model.get("calibration_sha256") != self.uncertainty_estimator.calibration_hash:
                raise ValueError("Benefit gate requires its recorded uncertainty calibration")
            if self.d3qn._checkpoint_hash not in self.benefit_gate.model.get("checkpoint_hashes", []):
                raise ValueError("Benefit gate has not been fitted for this checkpoint family")
        self._gate_allow = None
        self._gate_probability = None
        self._gate_low_steps = 0
        self._gate_evaluations = self._gate_vetoes = 0

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
        self._gate_allow = self._gate_probability = None
        self._gate_low_steps = self._gate_evaluations = self._gate_vetoes = 0

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

        stale = obs_age >= self.max_observation_age_ms
        supervisor_score = 1.0 if stale else u_score.score
        if self.benefit_gate is not None and self.enable_fallback:
            self._gate_low_steps = self._gate_low_steps + 1 if u_score.score <= self.supervisor.threshold_low else 0
            if self._gate_low_steps >= self.supervisor.recovery_window_steps:
                self._gate_allow = self._gate_probability = None
            # Decide once per uncertainty episode, never repeatedly search for a
            # favorable prediction each tick. Active fallback keeps its dwell.
            if (not stale and self.supervisor.authority == ControlAuthority.RL_ACTIVE
                    and u_score.score >= self.supervisor.threshold_high):
                if self._gate_allow is None:
                    self._gate_probability = self.benefit_gate.predict(observable_features(context, u_score.score))
                    self._gate_allow = (self._gate_probability is None or
                                       self._gate_probability >= self.benefit_gate.model["threshold"])
                    self._gate_evaluations += 1
                    self._gate_vetoes += int(not self._gate_allow)
                if not self._gate_allow:
                    supervisor_score = float(np.nextafter(self.supervisor.threshold_high, -np.inf))
        authority = (self.supervisor.update(supervisor_score, step=self._step_count)
                     if self.enable_fallback else ControlAuthority.RL_ACTIVE)
        self._last_authority = authority

        if authority == ControlAuthority.RL_ACTIVE:
            proposed_action = self.d3qn.act(observation, context)
            q_values = self.d3qn.get_diagnostics().get("q_values", [])
            active_controller = "d3qn"
        else:
            proposed_action = self.fallback.act(observation, context)
            q_values = []
            active_controller = f"{self.fallback.name}_fallback"

        if self.enable_shield and self.safety_shield is not None:
            shield_decision = self.safety_shield.filter_context(proposed_action, context)
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

        self._last_diagnostics = {
            "controller": "flowsync_uq",
            "active_controller": active_controller,
            "authority": authority.value,
            "uncertainty_score": round(u_score.score, 4),
            "stale_observation_failover": stale,
            "supervisor_score": supervisor_score,
            "benefit_gate_probability": self._gate_probability,
            "benefit_gate_allows_entry": self._gate_allow,
            "uncertainty_features": u_score.features.to_dict(),
            "phase_wait_semantics": context.extra_telemetry.get("phase_wait_semantics", "unspecified"),
            "proposed_action": proposed_action,
            "executed_action": executed_action,
            "was_overridden": shield_decision.was_overridden,
            "override_reason": shield_decision.override_reason,
            "q_values": q_values,
            "inference_time_ms": round(inference_time_ms, 3),
            "checkpoint_hash": self.d3qn._checkpoint_hash,
        }

        return executed_action

    def get_diagnostics(self) -> dict:
        policy = self.d3qn.get_diagnostics()
        return {**super().get_diagnostics(),
                **{k: policy.get(k) for k in ("checkpoint_hash", "checkpoint_path",
                   "checkpoint_loaded", "checkpoint_metadata", "deterministic")},
                "shield_enabled": self.enable_shield,
                "fallback_enabled": self.enable_fallback,
                "uncertainty_calibration_hash": self.uncertainty_estimator.calibration_hash,
                "benefit_gate_hash": self.benefit_gate.sha256 if self.benefit_gate else None,
                "benefit_gate_evaluations": self._gate_evaluations,
                "benefit_gate_vetoes": self._gate_vetoes,
                "supervisor": self.supervisor.get_audit_summary(),
                "shield": self.safety_shield.get_audit_metrics()}
