"""
statistical_pipeline.py — Statistical Hypothesis Testing and Effect Size Engine
================================================================================
Implements Task K1 and Task K2:
- Paired Common Random Number (CRN) differences.
- Shapiro-Wilk test for normality diagnostic.
- Paired Student's t-test and Wilcoxon Signed-Rank test.
- Percentile bootstrap 95% Confidence Intervals (10,000 resamples).
- Effect size calculations: Cohen's d and Cliff's delta.
- Holm-Bonferroni family-wise multiple testing correction.
- Practical significance evaluation against HCM/engineering margins.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from scipy import stats


PRACTICAL_SIGNIFICANCE_THRESHOLDS = {
    "mean_delay": {"rel_improvement_min": 0.05, "abs_improvement_min": 1.5, "higher_is_better": False},
    "p95_delay": {"rel_improvement_min": 0.10, "abs_improvement_min": 3.5, "higher_is_better": False},
    "queue_area": {"rel_improvement_min": 0.07, "abs_improvement_min": 100.0, "higher_is_better": False},
    "throughput": {"rel_improvement_min": 0.03, "abs_improvement_min": 25.0, "higher_is_better": True},
    "starvation_incidents": {"rel_improvement_min": 0.15, "abs_improvement_min": 1.0, "higher_is_better": False},
}


@dataclass
class StatisticalResult:
    metric_name: str
    baseline_mean: float
    baseline_std: float
    candidate_mean: float
    candidate_std: float
    mean_difference: float  # (baseline - candidate) if lower is better
    median_difference: float
    rel_improvement_pct: float
    ci_lower: float
    ci_upper: float
    shapiro_p: float
    is_normal: bool
    t_test_stat: float
    t_test_p: float
    wilcoxon_stat: float
    wilcoxon_p: float
    recommended_p: float
    cohens_d: float
    cliffs_delta: float
    is_statistically_significant: bool  # p < 0.05
    is_practically_significant: bool
    sample_size: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    """
    Computes Cliff's delta non-parametric effect size.
    d = (#(x > y) - #(x < y)) / (nx * ny)
    """
    n = len(x)
    if n == 0:
        return 0.0
    greater = 0
    less = 0
    for i in range(n):
        for j in range(n):
            if x[i] > y[j]:
                greater += 1
            elif x[i] < y[j]:
                less += 1
    return (greater - less) / (n * n)


def bootstrap_ci(
    data: np.ndarray,
    stat_func=np.mean,
    n_bootstraps: int = 10000,
    alpha: float = 0.05,
    seed: int = 42,
) -> Tuple[float, float]:
    """
    Computes percentile bootstrap confidence interval for a statistic.
    """
    rng = np.random.default_rng(seed)
    n = len(data)
    boot_stats = np.empty(n_bootstraps)
    for i in range(n_bootstraps):
        sample = rng.choice(data, size=n, replace=True)
        boot_stats[i] = stat_func(sample)
    lower = float(np.percentile(boot_stats, 100.0 * (alpha / 2.0)))
    upper = float(np.percentile(boot_stats, 100.0 * (1.0 - alpha / 2.0)))
    return lower, upper


def paired_difference_analysis(
    baseline_values: List[float],
    candidate_values: List[float],
    metric_name: str,
    higher_is_better: Optional[bool] = None,
    alpha: float = 0.05,
    n_bootstraps: int = 10000,
    seed: int = 42,
) -> StatisticalResult:
    """
    Executes full paired hypothesis testing under Common Random Numbers.
    """
    base = np.asarray(baseline_values, dtype=float)
    cand = np.asarray(candidate_values, dtype=float)

    if len(base) != len(cand):
        raise ValueError(f"Mismatched paired sample lengths: {len(base)} vs {len(cand)}")
    if len(base) < 3:
        raise ValueError("At least 3 paired samples required for statistical analysis.")

    # Determine direction
    if higher_is_better is None:
        if metric_name in PRACTICAL_SIGNIFICANCE_THRESHOLDS:
            higher_is_better = PRACTICAL_SIGNIFICANCE_THRESHOLDS[metric_name]["higher_is_better"]
        else:
            higher_is_better = False

    # Positive difference indicates improvement for candidate
    diffs = (cand - base) if higher_is_better else (base - cand)

    mean_base = float(np.mean(base))
    std_base = float(np.std(base, ddof=1)) if len(base) > 1 else 0.0
    mean_cand = float(np.mean(cand))
    std_cand = float(np.std(cand, ddof=1)) if len(cand) > 1 else 0.0

    mean_diff = float(np.mean(diffs))
    median_diff = float(np.median(diffs))

    # Relative improvement
    base_denom = abs(mean_base) if abs(mean_base) > 1e-6 else 1.0
    rel_improvement_pct = float((mean_diff / base_denom) * 100.0)

    # Bootstrap CI for mean difference
    ci_lower, ci_upper = bootstrap_ci(diffs, stat_func=np.mean, n_bootstraps=n_bootstraps, alpha=alpha, seed=seed)

    # Normality test of paired differences
    if len(diffs) >= 3 and not np.all(diffs == diffs[0]):
        shapiro_stat, shapiro_p = stats.shapiro(diffs)
    else:
        shapiro_stat, shapiro_p = 1.0, 1.0
    is_normal = bool(shapiro_p > 0.05)

    # Parametric: Paired t-test
    if np.all(diffs == 0.0):
        t_stat, t_p = 0.0, 1.0
    else:
        t_stat, t_p = stats.ttest_rel(base, cand) if not higher_is_better else stats.ttest_rel(cand, base)
    t_stat = float(t_stat)
    t_p = float(t_p)

    # Non-parametric: Wilcoxon signed-rank test
    if np.all(diffs == 0.0):
        w_stat, w_p = 0.0, 1.0
    else:
        try:
            w_stat, w_p = stats.wilcoxon(diffs, alternative="two-sided")
            w_stat = float(w_stat)
            w_p = float(w_p)
        except Exception:
            w_stat, w_p = 0.0, 1.0

    # Select primary recommended p-value based on normality check
    recommended_p = t_p if is_normal else w_p

    # Effect size: Cohen's d_z for paired data
    std_diff = float(np.std(diffs, ddof=1)) if len(diffs) > 1 else 0.0
    cohens_d = float(mean_diff / std_diff) if std_diff > 1e-6 else 0.0

    # Effect size: Cliff's delta
    cliffs_delta = compute_cliffs_delta(cand if higher_is_better else -cand, base if higher_is_better else -base)

    is_stat_sig = bool(recommended_p < alpha)

    # Practical significance check
    is_pract_sig = False
    if metric_name in PRACTICAL_SIGNIFICANCE_THRESHOLDS:
        thresh = PRACTICAL_SIGNIFICANCE_THRESHOLDS[metric_name]
        meets_rel = (rel_improvement_pct / 100.0) >= thresh["rel_improvement_min"]
        meets_abs = mean_diff >= thresh["abs_improvement_min"]
        is_pract_sig = bool(meets_rel or meets_abs)
    else:
        is_pract_sig = is_stat_sig

    return StatisticalResult(
        metric_name=metric_name,
        baseline_mean=mean_base,
        baseline_std=std_base,
        candidate_mean=mean_cand,
        candidate_std=std_cand,
        mean_difference=mean_diff,
        median_difference=median_diff,
        rel_improvement_pct=rel_improvement_pct,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        shapiro_p=float(shapiro_p),
        is_normal=is_normal,
        t_test_stat=t_stat,
        t_test_p=t_p,
        wilcoxon_stat=w_stat,
        wilcoxon_p=w_p,
        recommended_p=recommended_p,
        cohens_d=cohens_d,
        cliffs_delta=cliffs_delta,
        is_statistically_significant=is_stat_sig,
        is_practically_significant=is_pract_sig,
        sample_size=len(base),
    )


def adjust_p_values_holm_bonferroni(p_values: List[float]) -> List[float]:
    """
    Applies Holm-Bonferroni step-down family-wise error rate (FWER) correction.
    """
    m = len(p_values)
    if m <= 1:
        return p_values

    # Sort indices by original p-value
    sorted_indices = np.argsort(p_values)
    sorted_p = np.array(p_values)[sorted_indices]

    adjusted = np.empty(m)
    current_max = 0.0

    for i in range(m):
        # Adjusted p_k = min(1.0, (m - k) * p_k)
        val = min(1.0, (m - i) * sorted_p[i])
        current_max = max(current_max, val)
        adjusted[i] = current_max

    # Invert back to original ordering
    out = np.empty(m)
    out[sorted_indices] = adjusted
    return [float(x) for x in out]
