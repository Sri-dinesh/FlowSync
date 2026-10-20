"""
demand_forecast.py — Real-Time Short-Horizon Traffic Arrival Forecaster
========================================================================
Task 4.1: Implements an online Exponentially Weighted Moving Average (EWMA)
arrival rate tracker and short-horizon (5s, 10s, 20s) demand forecaster.

This is the core of FlowSync's predictive USP:
  Neither Greedy nor VAT can look into the future. By adding short-horizon
  EWMA arrival forecasting and queue growth rates to the state vector, the
  RL agent gains a structural predictive advantage over all reactive heuristics.

Usage:
    forecaster = ArrivalForecaster()
    forecaster.tick(dt=0.1, spawned_this_step=2)
    state_features = forecaster.get_forecast_features()
"""
from __future__ import annotations

from collections import deque
from typing import Deque, Dict

import numpy as np


    # Time constants in seconds; alpha is computed from dt to maintain exact filtering horizons.
_TAU_5S = 5.0
_TAU_10S = 10.0
_TAU_20S = 20.0

    # Normalization cap for extreme Poisson arrival rates.
_MAX_ARRIVAL_RATE = 2.0
_GROWTH_WINDOW_SECONDS = 10.0
_GROWTH_WINDOW_STEPS = int(_GROWTH_WINDOW_SECONDS / 0.1)  # 100 steps


class ArrivalForecaster:
    """
    Online EWMA-based arrival rate tracker and short-horizon demand forecaster.

    Tracks the rolling arrival rate at three time scales and computes
    a growth rate signal indicating whether demand is rising or falling.

    State output (8 features for dims 20-27 of the 28-D observation vector):
      [0] ewma_5s:       Normalized 5-second EWMA arrival rate
      [1] ewma_10s:      Normalized 10-second EWMA arrival rate
      [2] ewma_20s:      Normalized 20-second EWMA arrival rate
      [3] growth_rate:   Demand growth rate (ewma_5s - ewma_20s, normalized)
      [4] burst_flag:    1.0 if ewma_5s > 1.5 × ewma_20s (platoon detected)
      [5] dissipation:   1.0 if ewma_5s < 0.5 × ewma_20s (queue dissipating)
      [6] trend_signed:  Sign-magnitude of 10s trend (positive=rising, neg=falling)
      [7] absolute_rate: Raw instantaneous arrival rate / max_rate
    """

    def __init__(
        self,
        tau_5s: float = _TAU_5S,
        tau_10s: float = _TAU_10S,
        tau_20s: float = _TAU_20S,
        max_arrival_rate: float = _MAX_ARRIVAL_RATE,
    ) -> None:
        self._tau_5s = tau_5s
        self._tau_10s = tau_10s
        self._tau_20s = tau_20s
        self._max_rate = max_arrival_rate

        self._ewma_5s: float = 0.0
        self._ewma_10s: float = 0.0
        self._ewma_20s: float = 0.0

        self._rate_history: Deque[float] = deque(maxlen=_GROWTH_WINDOW_STEPS)

        self._instant_rate: float = 0.0
        self._total_arrivals: int = 0
        self._total_steps: int = 0

    def tick(self, dt: float, spawned_this_step: int) -> None:
        """
        Update EWMA state with new arrival data.

        Args:
            dt: Simulation timestep (seconds, typically 0.1).
            spawned_this_step: Number of vehicles spawned this tick.
        """
        instant_rate = spawned_this_step / dt if dt > 0 else 0.0
        self._instant_rate = instant_rate
        self._total_arrivals += spawned_this_step
        self._total_steps += 1

        alpha_5s = 1.0 - np.exp(-dt / max(self._tau_5s, 1e-6))
        alpha_10s = 1.0 - np.exp(-dt / max(self._tau_10s, 1e-6))
        alpha_20s = 1.0 - np.exp(-dt / max(self._tau_20s, 1e-6))
        self._ewma_5s  = (1 - alpha_5s)  * self._ewma_5s  + alpha_5s  * instant_rate
        self._ewma_10s = (1 - alpha_10s) * self._ewma_10s + alpha_10s * instant_rate
        self._ewma_20s = (1 - alpha_20s) * self._ewma_20s + alpha_20s * instant_rate

        self._rate_history.append(self._ewma_10s)

    def get_forecast_features(self) -> np.ndarray:
        """
        Return 8-element normalized feature vector for integration into state (dims 20-27).

        All values are clamped to [−1, 1] or [0, 1] depending on the feature semantics.
        """
        cap = max(self._max_rate, 1e-6)

        ewma_5s_norm  = min(1.0, self._ewma_5s / cap)
        ewma_10s_norm = min(1.0, self._ewma_10s / cap)
        ewma_20s_norm = min(1.0, self._ewma_20s / cap)

        # Growth rate: ewma_5s − ewma_20s; positive = demand rising (platoon incoming)
        growth = (self._ewma_5s - self._ewma_20s) / cap
        growth_clamped = max(-1.0, min(1.0, growth))

        # Burst flag: short-term rate exceeds 50% above long-term baseline (platoon detection).
        burst_flag = 1.0 if (
            self._ewma_20s > 0.05 and self._ewma_5s > 1.5 * self._ewma_20s
        ) else 0.0

        # Dissipation flag: rate dropped below 50% of baseline (queue clearance).
        dissipation = 1.0 if (
            self._ewma_20s > 0.05 and self._ewma_5s < 0.5 * self._ewma_20s
        ) else 0.0

        # Trend-signed: 10s EWMA compared to 20s baseline, normalized to [-1, 1]
        trend = (self._ewma_10s - self._ewma_20s) / cap
        trend_signed = max(-1.0, min(1.0, trend))

        absolute_rate = min(1.0, self._instant_rate / cap)

        return np.array(
            [
                ewma_5s_norm,
                ewma_10s_norm,
                ewma_20s_norm,
                growth_clamped,
                burst_flag,
                dissipation,
                trend_signed,
                absolute_rate,
            ],
            dtype=np.float32,
        )

    def get_debug_info(self) -> Dict[str, float]:
        """Return full state as labeled dict for logging and telemetry."""
        features = self.get_forecast_features()
        return {
            "ewma_5s":      float(features[0]),
            "ewma_10s":     float(features[1]),
            "ewma_20s":     float(features[2]),
            "growth_rate":  float(features[3]),
            "burst_flag":   float(features[4]),
            "dissipation":  float(features[5]),
            "trend_signed": float(features[6]),
            "abs_rate":     float(features[7]),
            "total_arrivals": self._total_arrivals,
        }

    def reset(self) -> None:
        """Reset all EWMA state (call at episode boundaries)."""
        self._ewma_5s = 0.0
        self._ewma_10s = 0.0
        self._ewma_20s = 0.0
        self._rate_history.clear()
        self._instant_rate = 0.0
        self._total_arrivals = 0
        self._total_steps = 0
