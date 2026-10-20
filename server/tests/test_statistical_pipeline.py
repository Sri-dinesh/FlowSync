"""
Tests for statistical analysis pipeline, effect sizes, and table generators (Phase K / Task K1 / Task K2).
"""

import tempfile
from pathlib import Path
import numpy as np
import pytest

from research.analysis.statistical_pipeline import (
    adjust_p_values_holm_bonferroni,
    bootstrap_ci,
    compute_cliffs_delta,
    paired_difference_analysis,
)
from research.analysis.table_generator import TableGenerator


def test_paired_difference_analysis_normal_improvement():
    # Candidate consistently achieves lower delay (e.g. 5s lower on average)
    rng = np.random.default_rng(101)
    baseline = rng.normal(loc=30.0, scale=3.0, size=25).tolist()
    candidate = [b - float(rng.normal(loc=5.0, scale=1.0)) for b in baseline]

    res = paired_difference_analysis(
        baseline_values=baseline,
        candidate_values=candidate,
        metric_name="mean_delay",
        higher_is_better=False,
    )

    assert res.mean_difference > 3.5
    assert res.rel_improvement_pct > 10.0
    assert res.ci_lower > 0.0  # Entire 95% CI strictly positive
    assert res.ci_upper > res.ci_lower
    assert res.is_statistically_significant is True
    assert res.is_practically_significant is True
    assert res.cohens_d > 0.8  # Large effect size
    assert res.cliffs_delta > 0.5


def test_paired_difference_analysis_no_difference():
    baseline = [25.0, 26.0, 24.5, 25.5, 27.0]
    candidate = [25.0, 26.0, 24.5, 25.5, 27.0]

    res = paired_difference_analysis(
        baseline_values=baseline,
        candidate_values=candidate,
        metric_name="mean_delay",
        higher_is_better=False,
    )

    assert res.mean_difference == 0.0
    assert res.rel_improvement_pct == 0.0
    assert res.is_statistically_significant is False
    assert res.is_practically_significant is False


def test_holm_bonferroni_adjustment():
    raw_p = [0.001, 0.012, 0.045, 0.20, 0.80]
    adj_p = adjust_p_values_holm_bonferroni(raw_p)

    assert len(adj_p) == len(raw_p)
    # Check monotonicity
    assert all(adj_p[i] <= adj_p[i + 1] for i in range(len(adj_p) - 1))
    # Adjusted p-values must be >= raw p-values
    for r, a in zip(raw_p, adj_p):
        assert a >= r
        assert a <= 1.0


def test_table_generator():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        records = [
            {
                "controller": "Fixed Timer",
                "mean_delay": 32.5,
                "std_delay": 2.1,
                "p95_delay": 58.2,
                "queue_area": 12500.0,
                "throughput": 820.0,
                "fallback_rate": 0.0,
                "shield_interventions": 0,
            },
            {
                "controller": "flowsync_uq",
                "mean_delay": 19.4,
                "std_delay": 1.5,
                "p95_delay": 34.0,
                "queue_area": 6200.0,
                "throughput": 990.0,
                "fallback_rate": 0.08,
                "shield_interventions": 0,
            },
        ]

        tex_file = tmp_path / "table_main.tex"
        tex_output = TableGenerator.generate_main_benchmark_latex(records, tex_file)

        assert tex_file.exists()
        assert r"\begin{table*}" in tex_output
        assert "flowsync_uq" in tex_output
        assert r"\bottomrule" in tex_output

        csv_file = tmp_path / "summary.csv"
        TableGenerator.export_csv(records, csv_file)
        assert csv_file.exists()
        csv_content = csv_file.read_text()
        assert "Fixed Timer" in csv_content
        assert "flowsync_uq" in csv_content
