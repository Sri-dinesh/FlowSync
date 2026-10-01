"""
Tests for ablation studies and failure taxonomy analysis (Phase J & Phase L).
"""

import tempfile
from pathlib import Path
import pytest

from research.experiments.run_ablations import build_ablation_controllers, run_ablation_experiments
from research.analysis.failure_analysis import (
    FailureMode,
    classify_run_failure,
    sweep_reliability_boundary,
)
from research.experiments.engine import ExperimentResult
from research.noise.fault_injector import FaultProfile


def test_ablation_controller_specifications():
    variants = build_ablation_controllers()
    assert "Full FlowSync-UQ" in variants
    assert "minus Uncertainty (No-UQ)" in variants
    assert "minus Safety Shield (No-Shield)" in variants
    assert "minus Fallback (No-Fallback)" in variants
    assert "minus MaxPressure (Fixed Fallback)" in variants

    # Check structural single-variable modifications
    full = variants["Full FlowSync-UQ"]
    assert full.enable_shield is True
    assert full.fallback_controller_name == "max_pressure"
    assert full.uncertainty_threshold == 0.45

    no_uq = variants["minus Uncertainty (No-UQ)"]
    assert no_uq.uncertainty_threshold > 100.0  # Inactive threshold

    no_shield = variants["minus Safety Shield (No-Shield)"]
    assert no_shield.enable_shield is False

    no_fb = variants["minus Fallback (No-Fallback)"]
    assert no_fb.fallback_controller_name == "d3qn"

    fixed_fb = variants["minus MaxPressure (Fixed Fallback)"]
    assert fixed_fb.fallback_controller_name == "fixed"


def test_failure_taxonomy_classification():
    dummy_res_nominal = ExperimentResult(
        experiment_id="exp_01",
        scenario_id="sc_01",
        scenario_hash="hash",
        controller_name="d3qn",
        seed=42,
        num_steps=1200,
        avg_delay=14.0,
        median_delay=13.0,
        p95_delay=32.0,
        std_delay=5.0,
        queue_area=1200.0,
        max_queue=12,
        total_vehicles_passed=500,
        total_arrivals=510,
        service_rate=0.98,
        starvation_count=0,
        watchdog_override_count=2,
        watchdog_override_rate=0.02,
        total_reward=100.0,
        elapsed_wall_seconds=0.5,
        controller_capabilities={},
    )

    rec_nominal = classify_run_failure(dummy_res_nominal)
    assert rec_nominal.is_failed is False
    assert FailureMode.NOMINAL.value in rec_nominal.failure_modes

    # Extreme spillback + starvation
    dummy_res_spillback = ExperimentResult(
        experiment_id="exp_02",
        scenario_id="sc_01",
        scenario_hash="hash",
        controller_name="d3qn",
        seed=42,
        num_steps=1200,
        avg_delay=35.0,
        median_delay=30.0,
        p95_delay=65.0,  # Extreme tail delay
        std_delay=15.0,
        queue_area=3500.0,
        max_queue=32,    # Spillback! (> 25)
        total_vehicles_passed=300,
        total_arrivals=510,
        service_rate=0.58,
        starvation_count=8,  # Starvation! (> 3)
        watchdog_override_count=0,
        watchdog_override_rate=0.0,
        total_reward=-500.0,
        elapsed_wall_seconds=0.5,
        controller_capabilities={},
    )

    rec_fail = classify_run_failure(dummy_res_spillback, unsafe_transitions=1)
    assert rec_fail.is_failed is True
    assert FailureMode.SPILLBACK.value in rec_fail.failure_modes
    assert FailureMode.STARVATION.value in rec_fail.failure_modes
    assert FailureMode.EXTREME_DELAY.value in rec_fail.failure_modes
    assert FailureMode.SAFETY_VIOLATION.value in rec_fail.failure_modes


def test_ablation_and_reliability_execution_smoke():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Fast ablation check
        res_ablation = run_ablation_experiments(
            scenario_ids=["train_mod_balanced_01"],
            seeds=[101],
            noise_profile=FaultProfile(name="test_miss", miss_rate=0.10),
            results_dir=tmp_path / "ablations",
        )
        assert len(res_ablation) == 5
        assert (tmp_path / "ablations" / "table_ablations.tex").exists()
        assert (tmp_path / "ablations" / "table_ablations.csv").exists()

        # Fast reliability boundary check
        res_boundary = sweep_reliability_boundary(
            scenario_id="train_mod_balanced_01",
            seeds=[101],
            miss_rates=[0.0, 0.20],
            controllers=["d3qn", "flowsync_uq"],
            results_dir=tmp_path / "reliability",
        )
        assert "d3qn" in res_boundary
        assert "flowsync_uq" in res_boundary
        assert (tmp_path / "reliability" / "reliability_boundary.json").exists()
        assert (tmp_path / "reliability" / "failure_registry.json").exists()
