#!/usr/bin/env python3
"""
Run flow calibration from a detection session JSON.

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
        description="Calibrate traffic flow parameters from a detection session."
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
    params = calibrator.calibrate_from_session(args.session)

    with open(args.output, "w") as f:
        json.dump(params.model_dump(mode="json"), f, indent=2)

    print(f"\n[Calibrate] Flow Parameters:")
    print(f"  Avg vehicles/min:  {params.avg_vehicles_per_minute:.1f}")
    print(f"  Vehicle dist:      {params.vehicle_type_distribution}")
    print(f"  Saved to:          {args.output}")


if __name__ == "__main__":
    main()
