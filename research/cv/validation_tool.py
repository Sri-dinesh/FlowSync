"""Legacy paired count-error helper; counts cannot establish object/track accuracy."""
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from server.app.simulation.traffic_math import MOVEMENT_KEYS
from research.uncertainty.estimator import PerceptionUncertaintyEstimator


@dataclass
class CVValidationReport:
    total_frames_evaluated: int
    count_mae: float
    count_rmse: float
    uncertainty_error_correlation: float | None
    precision: None = None
    recall: None = None
    f1_score: None = None
    lane_assignment_accuracy_pct: None = None
    arrival_time_mae_s: None = None
    scope: str = "paired count errors only; no object correspondence, tracking or event timing labels"
    lane_errors: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CVStateValidator:
    def evaluate(self, predicted_frames, annotated_frames) -> CVValidationReport:
        if not predicted_frames or len(predicted_frames) != len(annotated_frames):
            raise ValueError("Nonempty paired frame lists of equal length are required.")
        errors, scores, differences = [], [], []
        estimator = PerceptionUncertaintyEstimator()
        for predicted, annotated in zip(predicted_frames, annotated_frames):
            vectors = []
            for row in (predicted, annotated):
                counts = row["lane_counts"]
                if any(key not in MOVEMENT_KEYS or type(value) not in (int, float)
                       or not np.isfinite(value) or value < 0 for key, value in counts.items()):
                    raise ValueError("Counts must have known movement keys and finite nonnegative values.")
                vectors.append(np.array([counts.get(key, 0) for key in MOVEMENT_KEYS], dtype=float))
            differences.append(vectors[0]-vectors[1])
            errors.append(float(np.linalg.norm((vectors[0]-vectors[1])/10)))
            confidences = predicted.get("confidences")
            if confidences:
                if any(type(c) not in (int, float) or not np.isfinite(c) or not 0 <= c <= 1 for c in confidences):
                    raise ValueError("Detection confidences must be finite values in [0, 1].")
                scores.append(estimator.compute(observed_queues=vectors[0]/10, detection_confidences=confidences).score)
        corr = None
        if len(errors) > 5 and len(scores) == len(errors) and np.std(errors) > 1e-6 and np.std(scores) > 1e-6:
            corr = float(np.corrcoef(scores, errors)[0, 1])
        array = np.array(differences)
        return CVValidationReport(
            total_frames_evaluated=len(array), count_mae=float(np.abs(array).mean()),
            count_rmse=float(np.sqrt((array**2).mean())), uncertainty_error_correlation=corr,
            lane_errors=dict(zip(MOVEMENT_KEYS, np.abs(array).mean(axis=0).tolist())),
        )
