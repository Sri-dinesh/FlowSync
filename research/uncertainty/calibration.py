"""
calibration.py — Uncertainty Calibration and Threshold Tuning
==============================================================
Task 1A.3 & Task C2: Calibrates the relationship between estimated uncertainty
and true state-estimation error on validation datasets.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import numpy as np
import scipy.stats as stats


@dataclass
class CalibrationReport:
    """Calibration diagnostic statistics on validation data."""
    pearson_r: float
    spearman_rho: float
    p_value: float
    roc_auc: float
    ece: float  # Expected Calibration Error
    recommended_t_high: float
    recommended_t_low: float
    sample_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pearson_r": round(self.pearson_r, 4),
            "spearman_rho": round(self.spearman_rho, 4),
            "p_value": self.p_value,
            "roc_auc": round(self.roc_auc, 4),
            "ece": round(self.ece, 4),
            "recommended_t_high": round(self.recommended_t_high, 4),
            "recommended_t_low": round(self.recommended_t_low, 4),
            "sample_count": self.sample_count,
        }


def compute_calibration_metrics(
    uncertainty_scores: np.ndarray,
    actual_state_errors: np.ndarray,
    high_error_quantile: float = 0.75,
    num_bins: int = 10,
) -> CalibrationReport:
    """
    Evaluate statistical association between uncertainty score and actual L2 state error.

    Args:
        uncertainty_scores: 1D array of estimated uncertainty in [0, 1].
        actual_state_errors: 1D array of true L2 state differences ||s_obs - s_true||_2.
        high_error_quantile: Threshold quantile defining 'ground truth failure' for ROC-AUC.
        num_bins: Number of bins for Expected Calibration Error (ECE).
    """
    assert len(uncertainty_scores) == len(actual_state_errors)
    n = len(uncertainty_scores)
    if n < 5:
        raise ValueError("Calibration requires at least 5 samples.")

    # 1. Pearson and Spearman correlations
    r, p_val = stats.pearsonr(uncertainty_scores, actual_state_errors)
    rho, _ = stats.spearmanr(uncertainty_scores, actual_state_errors)

    # 2. Binary classification target: error in upper quartile
    threshold_error = float(np.percentile(actual_state_errors, high_error_quantile * 100))
    binary_targets = (actual_state_errors >= threshold_error).astype(int)

    # 3. ROC-AUC calculation (Mann-Whitney U statistic equivalent)
    positives = uncertainty_scores[binary_targets == 1]
    negatives = uncertainty_scores[binary_targets == 0]
    if len(positives) > 0 and len(negatives) > 0:
        u_stat, _ = stats.mannwhitneyu(positives, negatives, alternative="greater")
        roc_auc = float(u_stat / (len(positives) * len(negatives)))
    else:
        roc_auc = 0.5

    # 4. Expected Calibration Error (ECE) across bins
    bins = np.linspace(0.0, 1.0, num_bins + 1)
    ece = 0.0
    for i in range(num_bins):
        in_bin = (uncertainty_scores >= bins[i]) & (uncertainty_scores < bins[i + 1])
        bin_size = np.sum(in_bin)
        if bin_size > 0:
            bin_conf = np.mean(uncertainty_scores[in_bin])
            bin_acc = np.mean(binary_targets[in_bin])
            ece += (bin_size / n) * abs(bin_conf - bin_acc)

    # 5. Recommended thresholds from empirical quantiles
    # T_high: threshold identifying upper 25% error states
    # T_low: safe recovery threshold below 40th percentile
    t_high = float(np.percentile(uncertainty_scores, 75))
    t_low = float(np.percentile(uncertainty_scores, 40))
    if t_low >= t_high:
        t_low = t_high * 0.65

    return CalibrationReport(
        pearson_r=float(r),
        spearman_rho=float(rho),
        p_value=float(p_val),
        roc_auc=float(roc_auc),
        ece=float(ece),
        recommended_t_high=t_high,
        recommended_t_low=t_low,
        sample_count=n,
    )
