"""Exercise package discovery and relocated entry points without running jobs."""
from pathlib import Path
import subprocess
import sys

import pytest

from research.scenarios.loader import load_scenario
from research.scenarios.scenario_schema import ScenarioConfig

ROOT = Path(__file__).resolve().parents[2]


def test_research_discovery_does_not_import_training_or_start_a_job():
    script = """
import runpy
import sys
sys.argv = ['research']
try:
    runpy.run_module('research', run_name='__main__')
except SystemExit as exc:
    assert exc.code == 0
assert 'torch' not in sys.modules
assert 'research.training.train_policy' not in sys.modules
"""
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert "compare-spatial" in result.stdout and "export-paper" in result.stdout


def test_research_command_passes_help_to_the_selected_tool():
    result = subprocess.run([sys.executable, "-m", "research", "compare-spatial", "--help"],
                            cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert "batch" in result.stdout
    assert "{train,evaluate" not in result.stdout


def test_relocated_training_script_finds_repository_from_another_directory(tmp_path):
    result = subprocess.run([sys.executable, str(ROOT / "research/training/train_policy.py"), "--help"],
                            cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert "--output" in result.stdout and "--observation-version" in result.stdout
    assert not list(tmp_path.iterdir())


def test_scenario_id_and_explicit_path_agree_outside_repository(tmp_path, monkeypatch):
    source = ROOT / "research/scenarios/train/train_mod_balanced_01.yaml"
    expected = ScenarioConfig.load(source).to_dict()
    monkeypatch.chdir(tmp_path)
    assert load_scenario("train_mod_balanced_01").to_dict() == expected
    assert load_scenario(str(source)).to_dict() == expected
    with pytest.raises(FileNotFoundError, match="Could not locate scenario"):
        load_scenario("unknown_scenario")


def test_explicit_research_timing_does_not_import_api_credentials():
    script = """
import importlib.abc
import sys
class BlockAPISettings(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in {'app.config', 'server.app.config'}:
            raise AssertionError('Explicit simulation timing must not load API credentials')
sys.meta_path.insert(0, BlockAPISettings())
from research.experiments.runtime import build_environment
from research.scenarios.loader import load_scenario
scenario = load_scenario('train_mod_balanced_01')
env, _ = build_environment(scenario)
env.reset(seed=101)
env.step(0)
assert env.intersection.signal.red_duration == scenario.red_duration
"""
    result = subprocess.run([sys.executable, "-c", script], cwd=ROOT,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
