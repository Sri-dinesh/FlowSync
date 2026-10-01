"""
Tests for one-command research reproduction suite (Phase O / Task O1).
"""

import tempfile
from pathlib import Path
import pytest
import subprocess
import sys


def test_reproduce_all_quick_smoke():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Run reproduce_all script in quick mode
        cmd = [
            sys.executable,
            "scripts/reproduce_all.py",
            "--quick",
            "--output-dir",
            str(tmp_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        assert result.returncode == 0, f"reproduce_all failed: {result.stderr}"

        # Verify key deliverables exist
        assert (tmp_path / "git_commit.txt").exists()
        assert (tmp_path / "environment.json").exists()
        assert (tmp_path / "statistical_report.json").exists()
        assert (tmp_path / "tables" / "table_benchmark_comparison.tex").exists()
        assert (tmp_path / "tables" / "table_noise_robustness.tex").exists()
        assert (tmp_path / "ablations" / "table_ablations.tex").exists()
        assert (tmp_path / "sensitivity" / "table_threshold_sweep.csv").exists()
        assert (tmp_path / "reliability" / "reliability_boundary.json").exists()
        assert (tmp_path / "scalability" / "table_city_2x2_scalability.tex").exists()
        assert (tmp_path / "profiling" / "latency_profile.json").exists()
        assert (tmp_path / "shadow_mode" / "table_shadow_replay.tex").exists()
