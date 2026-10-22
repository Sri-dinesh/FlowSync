"""Retired pre-audit commands must refuse execution without changing artifacts."""
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("mode", ["--quick", "--full", "--final"])
def test_retired_reproduction_suite_refuses_and_preserves_outputs(tmp_path, mode):
    sentinel = tmp_path / "existing-result.json"
    sentinel.write_text('{"preserve": true}\n')
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/reproduce_all.py"), mode,
         "--output-dir", str(tmp_path)],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "explicit compatible checkpoints" in result.stderr
    assert sentinel.read_text() == '{"preserve": true}\n'
    assert list(tmp_path.iterdir()) == [sentinel]
