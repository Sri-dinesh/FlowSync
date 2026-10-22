"""Freeze parent checkpoints, sources and the matched spatial-input protocol."""
from prepare_margin_pilot import prepare


if __name__ == "__main__":
    print(prepare(prefix="spatial_v9_", launcher="run_spatial_pilot.sh",
                  protocol="SPATIAL_PILOT_PROTOCOL_20261021.md",
                  extra_sources=("SPATIAL_INPUT_EXPERIMENT_PLAN_20261021.md",)))
