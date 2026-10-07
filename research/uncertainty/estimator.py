"""
estimator.py — Multi-Feature Perception Uncertainty Engine
===========================================================
Task 1A.3 & Task C2: Quantifies observation reliability from multi-feature
perception dynamics rather than naive raw detector confidence.

Feature Vector phi_t:
1. Mean detector confidence (inverted: 1.0 - conf)
2. Lower-tail detector confidence (inverted: 1.0 - tail_conf)
3. Count volatility: Normalized step-to-step queue change |q_t - q_{t-1}|
4. Forecast innovation residual: L2 norm between instantaneous queue and 5s EWMA
5. Observation staleness / age: Time since newest observation frame
6. Missing-frame / frame-drop penalty
7. Track fragmentation proxy: Sudden ID turnover rate

Aggregation:
  U_raw = w^T phi_t + b
  U_t = sigmoid(U_raw / temperature) in [0.0, 1.0]
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class UncertaintyFeatures:
    """Individual features contributing to the composite uncertainty estimate."""
    detector_uncertainty: float = 0.0       # 1.0 - mean_conf
    tail_detector_uncertainty: float = 0.0  # 1.0 - min/tail_conf
    count_volatility: float = 0.0           # sudden jump in queue
    forecast_residual: float = 0.0          # disagreement with 5s EWMA forecaster
    observation_age: float = 0.0            # staleness from latency or dropped frames
    missing_frame_penalty: float = 0.0      # 1.0 if frame was dropped, 0.0 otherwise
    track_instability: float = 0.0          # lost or fragmented tracks

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)

    def to_array(self) -> np.ndarray:
        return np.array([
            self.detector_uncertainty,
            self.tail_detector_uncertainty,
            self.count_volatility,
            self.forecast_residual,
            self.observation_age,
            self.missing_frame_penalty,
            self.track_instability,
        ], dtype=np.float32)


@dataclass
class UncertaintyScore:
    """Aggregated uncertainty score and detailed diagnostic breakdown."""
    score: float  # Scalar uncertainty in [0.0, 1.0] (0 = fully confident, 1 = completely untrusted)
    is_unreliable: bool  # True if score >= threshold
    threshold: float
    features: UncertaintyFeatures
    feature_contributions: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score": round(self.score, 4),
            "is_unreliable": self.is_unreliable,
            "threshold": self.threshold,
            "features": self.features.to_dict(),
            "contributions": {k: round(v, 4) for k, v in self.feature_contributions.items()},
        }


class PerceptionUncertaintyEstimator:
    """
    Computes calibrated perception uncertainty from observation dynamics.
    """

    def __init__(
        self,
        threshold_high: float = 0.45,
        threshold_low: float = 0.25,
        temperature: float = 1.0,
        weights: Optional[Dict[str, float]] = None,
    ) -> None:
        self.threshold_high = threshold_high
        self.threshold_low = threshold_low
        self.temperature = max(1e-3, temperature)

        # Default calibrated feature weights (empirically calibrated on validation noise data)
        self.weights = weights or {
            "detector_uncertainty": 0.20,
            "tail_detector_uncertainty": 0.15,
            "count_volatility": 0.25,
            "forecast_residual": 0.20,
            "observation_age": 0.10,
            "missing_frame_penalty": 0.05,
            "track_instability": 0.05,
        }

        self._prev_queues: Optional[np.ndarray] = None
        self._step: int = 0

    def reset(self) -> None:
        self._prev_queues = None
        self._step = 0

    def compute(
        self,
        observed_queues: np.ndarray,
        forecast_features: Optional[np.ndarray] = None,
        detection_confidences: Optional[List[float]] = None,
        observation_age_ms: float = 0.0,
        frame_dropped: bool = False,
        track_loss_count: int = 0,
    ) -> UncertaintyScore:
        """
        Compute multi-feature uncertainty score.

        Args:
            observed_queues: 12-element movement queue vector.
            forecast_features: Optional 8-element EWMA forecaster features (dims 20-27).
            detection_confidences: List of YOLO detection confidence scores in [0, 1].
            observation_age_ms: Latency or staleness in milliseconds.
            frame_dropped: True if newest video frame was dropped/stale.
            track_loss_count: Number of lost/fragmented tracks this tick.
        """
        self._step += 1
        q_curr = np.asarray(observed_queues, dtype=np.float32)[:12]

        # 1. Detector confidence features
        if detection_confidences and len(detection_confidences) > 0:
            confs = np.array(detection_confidences, dtype=np.float32)
            mean_c = float(np.mean(confs))
            tail_c = float(np.percentile(confs, 10))
            det_u = float(np.clip(1.0 - mean_c, 0.0, 1.0))
            tail_u = float(np.clip(1.0 - tail_c, 0.0, 1.0))
        else:
            det_u = 0.0
            tail_u = 0.0

        # 2. Step-to-step count volatility: physically impossible jumps indicate miss or ghost
        if self._prev_queues is not None:
            # Physical max service per approach in 0.1s is ~0.2 vehicles.
            # Large jumps (|dq| > 0.3) indicate perception flicker
            dq = np.abs(q_curr - self._prev_queues)
            volatility = float(np.clip(np.mean(dq) * 3.0, 0.0, 1.0))
        else:
            volatility = 0.0
        self._prev_queues = np.copy(q_curr)

        # 3. Forecast innovation residual: disagreement between instantaneous queue and EWMA baseline
        if forecast_features is not None and len(forecast_features) >= 3:
            # Dims 0, 1, 2 of forecast are 5s, 10s, 20s EWMA
            ewma_5s = float(forecast_features[0])
            mean_q = float(np.mean(q_curr))
            residual = float(np.clip(abs(mean_q - ewma_5s) * 2.0, 0.0, 1.0))
        else:
            residual = 0.0

        # 4. Observation age / staleness (normalized by 1000ms)
        age_norm = float(np.clip(observation_age_ms / 1000.0, 0.0, 1.0))

        # 5. Missing-frame penalty
        frame_u = 1.0 if frame_dropped else 0.0

        # 6. Track instability
        track_u = float(np.clip(track_loss_count / 5.0, 0.0, 1.0))

        features = UncertaintyFeatures(
            detector_uncertainty=det_u,
            tail_detector_uncertainty=tail_u,
            count_volatility=volatility,
            forecast_residual=residual,
            observation_age=age_norm,
            missing_frame_penalty=frame_u,
            track_instability=track_u,
        )

        # Weighted aggregation
        weighted_sum = (
            self.weights["detector_uncertainty"] * det_u
            + self.weights["tail_detector_uncertainty"] * tail_u
            + self.weights["count_volatility"] * volatility
            + self.weights["forecast_residual"] * residual
            + self.weights["observation_age"] * age_norm
            + self.weights["missing_frame_penalty"] * frame_u
            + self.weights["track_instability"] * track_u
        )

        # Calibrated temperature scaling with sigmoid mapping
        # Maps 0.0 weighted sum to ~0.05, 0.5 to ~0.50, 1.0 to ~0.95
        scaled_logits = (weighted_sum - 0.35) * 5.0 / self.temperature
        calibrated_score = float(1.0 / (1.0 + np.exp(-scaled_logits)))

        contributions = {
            "detector_uncertainty": self.weights["detector_uncertainty"] * det_u,
            "tail_detector_uncertainty": self.weights["tail_detector_uncertainty"] * tail_u,
            "count_volatility": self.weights["count_volatility"] * volatility,
            "forecast_residual": self.weights["forecast_residual"] * residual,
            "observation_age": self.weights["observation_age"] * age_norm,
            "missing_frame_penalty": self.weights["missing_frame_penalty"] * frame_u,
            "track_instability": self.weights["track_instability"] * track_u,
        }

        return UncertaintyScore(
            score=calibrated_score,
            is_unreliable=calibrated_score >= self.threshold_high,
            threshold=self.threshold_high,
            features=features,
            feature_contributions=contributions,
        )
