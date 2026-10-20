"""Freeze the same three selected parents and the temporal pilot protocol."""
from prepare_margin_pilot import prepare


if __name__ == "__main__":
    print(prepare(prefix="temporal_v8_", launcher="run_temporal_pilot.sh",
                  protocol="TEMPORAL_INPUT_EXPERIMENT_PLAN.md"))
