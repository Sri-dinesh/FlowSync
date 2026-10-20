"""Freeze the existing parents and the low-update development protocol."""
from prepare_margin_pilot import prepare


if __name__ == "__main__":
    print(prepare(prefix="update_pressure_", launcher="run_update_pressure_pilot.sh",
                  protocol="UPDATE_PRESSURE_PROTOCOL_20261016.md"))
