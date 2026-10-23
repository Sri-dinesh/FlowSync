"""Freeze the same three selected parents and the temporal pilot protocol."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research.pilots.prepare_margin_pilot import prepare


if __name__ == "__main__":
    print(prepare(prefix="temporal_v8_", launcher="run_temporal_pilot.sh",
                  protocol="TEMPORAL_INPUT_EXPERIMENT_PLAN.md"))
