"""Exercise the shell launcher with a stub, never real training."""
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("worker_exit", [0, 7])
def test_pilot_flags_and_worker_failure_reporting(tmp_path, worker_exit):
    executable = tmp_path / "server/venv/bin/python"
    executable.parent.mkdir(parents=True)
    executable.write_text(f'#!/bin/sh\nprintf \'%s\\n\' "$@"\nexit {worker_exit}\n')
    executable.chmod(0o700)
    research = tmp_path / "research/training"
    research.mkdir(parents=True)
    (research / "train_policy.py").touch()
    result = subprocess.run(["bash", str(ROOT / "research/pilots/launchers/run_learning_pilot.sh")],
                            cwd=tmp_path, capture_output=True, text=True, timeout=10)
    assert result.returncode == int(worker_exit != 0)
    assert f"Failed-process flag: {int(worker_exit != 0)}" in result.stdout
    batches = list((tmp_path / "results/research_training").glob("pilot_v5_*"))
    assert len(batches) == 1
    for seed in (101, 202, 303):
        args = (batches[0] / f"seed_{seed}.log").read_text().splitlines()
        for flag, value in (("--seed", str(seed)), ("--episodes", "900"),
                            ("--max-wall-seconds", "600"), ("--validate-every", "50")):
            assert args[args.index(flag) + 1] == value
        assert "--train-with-shield" in args
