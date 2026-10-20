"""Opt-in observable-only gate for uncertainty-driven (not hard stale) fallback.

Predicts a training-defined short-horizon outcome, not a safety guarantee.
"""
import hashlib
import json
from pathlib import Path

import numpy as np

from server.app.simulation.traffic_signal import PHASE_DEMAND_MOVEMENTS

FEATURE_NAMES = ["uncertainty", "observation_age_s", "phase_demand_total", "current_demand_share",
                 "alternative_demand_advantage", "max_phase_service_timer", "green_age", "can_switch"]


def observable_features(context, uncertainty):
    queues = context.movement_queues or {}
    counts = [sum(queues.get(m, 0.) for m in PHASE_DEMAND_MOVEMENTS[p]) for p in range(4)]
    current = counts[context.current_phase]
    alternative = max(counts[p] for p in range(4) if p != context.current_phase)
    return [float(uncertainty), float(context.extra_telemetry.get("observation_age_ms", 0.))/1000.,
            sum(counts)/15., current/max(1., sum(counts)), (alternative-current)/15.,
            max((context.phase_starvation_times or {}).values(), default=0.)/45.,
            context.time_in_phase/40., float(context.can_switch_phase)]


class FallbackBenefitGate:
    def __init__(self, path):
        raw = Path(path).read_bytes()
        model = json.loads(raw)
        if model.get("version") != "fallback_benefit_logistic_v1" or model.get("feature_names") != FEATURE_NAMES:
            raise ValueError("Incompatible fallback benefit gate")
        for key in ("mean", "scale", "coefficients"):
            value = np.asarray(model[key], dtype=float)
            if value.shape != (len(FEATURE_NAMES),) or not np.isfinite(value).all():
                raise ValueError(f"Invalid benefit gate {key}")
        if min(model["scale"]) <= 0 or not np.isfinite(model["intercept"]) or not 0 < model["threshold"] < 1:
            raise ValueError("Invalid benefit gate scale, intercept or threshold")
        self.model = model
        self.sha256 = hashlib.sha256(raw).hexdigest()

    def predict(self, features):
        values = np.asarray(features, dtype=float)
        if values.shape != (len(FEATURE_NAMES),) or not np.isfinite(values).all():
            return None  # Preserve the original supervisor when inputs are invalid.
        z = (values-self.model["mean"])/self.model["scale"]
        logit = z @ np.asarray(self.model["coefficients"]) + self.model["intercept"]
        return float(1./(1.+np.exp(-np.clip(logit, -60., 60.))))
