"""
Tests for 2x2 network scalability, real-time latency profiling, and shadow-mode replay (Phase M / Task M1 / Task M2 / Task F3).
"""

import tempfile
from pathlib import Path
import pytest

from research.experiments.run_city_scalability import run_city_network_experiment, run_scalability_benchmark
from research.profiling.latency_profiler import profile_pipeline_latency, get_hardware_info
from research.cv.shadow_mode_replay import generate_empirical_replay_schedule, evaluate_shadow_replay


def test_hardware_info_capture():
    info = get_hardware_info()
    assert "os" in info
    assert "processor" in info
    assert "torch_version" in info
    assert "device" in info


def test_city_network_2x2_experiment():
    res = run_city_network_experiment(
        controller_name="fixed",
        duration_steps=50,  # 5s smoke test
        seed=42,
    )
    assert res["controller"] == "fixed"
    assert res["network_topology"] == "2x2_grid_4_intersections"
    assert "mean_delay" in res
    assert "network_throughput" in res
    assert res["total_decisions"] > 0


def test_latency_profiler_smoke():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        report = profile_pipeline_latency(
            num_decisions=200,
            warmup_steps=20,
            results_dir=tmp_path / "profiling",
        )
        assert report["num_decisions_evaluated"] == 200
        assert "end_to_end_pipeline" in report["stages"]
        assert report["stages"]["end_to_end_pipeline"]["p95_ms"] > 0.0
        # Check files were written
        assert (tmp_path / "profiling" / "latency_profile.json").exists()
        assert (tmp_path / "profiling" / "table_latency_profile.tex").exists()


def test_shadow_mode_replay_smoke():
    sched = generate_empirical_replay_schedule(duration_steps=200, seed=123)
    assert len(sched) > 0

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        records = evaluate_shadow_replay(
            controller_names=["fixed", "max_pressure"],
            seeds=[101],
            duration_steps=100,  # 10s smoke
            results_dir=tmp_path / "shadow",
        )
        assert len(records) == 2
        assert (tmp_path / "shadow" / "table_shadow_replay.csv").exists()
        assert (tmp_path / "shadow" / "table_shadow_replay.tex").exists()
