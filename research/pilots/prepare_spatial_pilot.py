"""Freeze parent checkpoints, sources and the matched spatial-input protocol."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research.pilots.prepare_margin_pilot import prepare


if __name__ == "__main__":
    print(prepare(prefix="spatial_v9_", launcher="run_spatial_pilot.sh",
                  protocol="SPATIAL_PILOT_PROTOCOL_20261021.md",
                  extra_sources=("SPATIAL_INPUT_EXPERIMENT_PLAN_20261021.md",)))
