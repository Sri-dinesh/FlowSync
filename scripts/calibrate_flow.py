#!/usr/bin/env python3
"""
Count declared upstream arrival events over an explicit observation interval.

Usage:
    python scripts/calibrate_flow.py --session data/sessions/session_001.json --output data/flow_params.json
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "server"))


def main():
    parser = argparse.ArgumentParser(
        description="Estimate supplied upstream-event rates; occupancy-only sessions are rejected."
    )
    parser.add_argument("--session", type=str, required=True, help="Path to session JSON file")
    parser.add_argument("--output", type=str, default="data/flow_params.json", help="Output path")
    args = parser.parse_args()

    if not Path(args.session).exists():
        print(f"ERROR: Session file not found: {args.session}")
        sys.exit(1)

    from app.realworld.digital_twin.flow_calibrator import FlowCalibrator

    calibrator = FlowCalibrator()
    print(f"[Calibrate] Loading session: {args.session}")
    try:
        params = calibrator.calibrate_from_session(args.session)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    if Path(args.output).exists():
        parser.error("Output already exists; use a new path to preserve evidence")
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    with open(args.output, "w") as f:
        json.dump(calibrator.export_as_simulation_config(params), f, indent=2, allow_nan=False)

    print(f"\n[Calibrate] Flow Parameters:")
    print(f"  Avg vehicles/min:  {params.avg_vehicles_per_minute:.1f}")
    print(f"  Vehicle dist:      {params.vehicle_type_distribution}")
    print(f"  Saved to:          {args.output}")


if __name__ == "__main__":
    main()
