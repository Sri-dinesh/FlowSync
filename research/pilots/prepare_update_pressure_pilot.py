"""Freeze the existing parents and the low-update development protocol."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from research.pilots.prepare_margin_pilot import prepare


if __name__ == "__main__":
    print(prepare(prefix="update_pressure_", launcher="run_update_pressure_pilot.sh",
                  protocol="UPDATE_PRESSURE_PROTOCOL_20261016.md"))
