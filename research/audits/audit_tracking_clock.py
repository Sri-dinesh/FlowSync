"""Reproduce processing-clock dependence using fixed synthetic detections."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pydantic

from server.app.realworld.models.calibration import CameraCalibration
from server.app.realworld.models.schemas import BoundingBox, VehicleDetection
from server.app.realworld.pipeline.camera_geometry import assign_approaches
from server.app.realworld.pipeline.stop_line_crossings import StopLineCrossings
from server.app.realworld.pipeline.vehicle_tracker import VehicleTracker

ROOT = Path(__file__).resolve().parents[2]
TRACKER = "server/app/realworld/pipeline/vehicle_tracker.py"
BASELINE = "0918643"
BASELINE_SHA256 = "892276c3bbf90abac0dc5320ce18f85db63a27841fc101e560c9ac8107223276"
CASES = {
    "fast_processing": ([10., 10.1], [0., .5]),
    "slow_processing": ([10., 14.], [0., .5]),
    "wall_clock_backwards": ([10., 1.], [0., .5]),
    "video_time_gap": ([10., 10.1], [0., 4.]),
}
SOURCES = (
    "research/audits/audit_tracking_clock.py", TRACKER,
    "server/app/realworld/pipeline/camera_geometry.py", "server/app/realworld/pipeline/stop_line_crossings.py",
    "server/app/realworld/models/calibration.py", "server/app/realworld/models/crossings.py",
    "server/app/realworld/models/schemas.py", "server/app/realworld/models/config.py",
    "server/app/realworld/models/signal_timeline.py",
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def measure(baseline_source):
    if digest(baseline_source) != BASELINE_SHA256:
        raise ValueError("Baseline tracker source hash mismatch.")
    baseline = {"__name__": "tracking_clock_baseline", "__package__": "server.app.realworld.pipeline"}
    exec(compile(baseline_source, "baseline_tracker.py", "exec"), baseline)
    calibration = CameraCalibration(camera_id="clock_fixture", source="synthetic_detections", frame_width=1000, frame_height=1000,
        approaches=[dict(approach="north", vertices=[[.1,.1],[.4,.1],[.4,.6],[.1,.6]], stop_line=[[.15,.6],[.35,.6]])])
    cases = {}
    for name, (wall_times, video_times) in CASES.items():
        arms = {}
        for arm in ("baseline", "corrected"):
            tracker = baseline["VehicleTracker"]() if arm == "baseline" else VehicleTracker()
            tracker.reset()
            crossings = StopLineCrossings(calibration)
            ids, events = [], []
            for frame, (wall, source, y) in enumerate(zip(wall_times, video_times, (580, 620)), 1):
                packet = VehicleDetection(frame_id=frame, timestamp_ms=wall*1000, frame_width=1000, frame_height=1000,
                    bboxes=[BoundingBox(x1=245, x2=255, y1=y-10, y2=y, confidence=.9, class_id=2, class_name="car")])
                if arm == "baseline":
                    baseline["time"] = SimpleNamespace(time=lambda: wall)
                    packet = tracker.update(packet)
                else:
                    packet = tracker.update(packet, observation_time_s=source)
                ids.append(packet.bboxes[0].track_id)
                assignments, geometry = assign_approaches(packet, calibration)
                events.extend(event.model_dump(mode="json") for event in crossings.update(packet, assignments, geometry, source).events)
            arms[arm] = dict(track_ids=ids, crossing_count=len(events), crossings=events)
        cases[name] = dict(processing_wall_times_s=wall_times, video_times_s=video_times, **arms)
    return dict(schema_version="tracking_clock_audit_v1", complete=True,
                baseline_revision=BASELINE, baseline_sha256=BASELINE_SHA256,
                calibration=calibration.model_dump(mode="json"), cases=cases,
                scope="Fixed synthetic boxes through actual tracker, geometry and crossing code. No detector, video decoder, traffic simulator or physical signal was run. Processing clocks are injected, not benchmarked runtimes.",
                publication_ready=False, policy_promoted=False, physical_actuation=False,
                python_version=sys.version, pydantic_version=pydantic.__version__)


def build_report(baseline_source):
    report = measure(baseline_source)
    sources = {name: (ROOT/name).read_bytes() for name in SOURCES}
    report["source_sha256"] = {name: digest(data) for name, data in sources.items()}
    return report, sources


def run(output):
    baseline = subprocess.check_output(["git", "show", f"{BASELINE}:{TRACKER}"], cwd=ROOT)
    report, sources = build_report(baseline)
    output.mkdir(parents=True, exist_ok=False)
    (output/"baseline_tracker.py").write_bytes(baseline)
    for name, data in sources.items():
        path = output/"source"/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (output/"report.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    return report


def verify(output):
    report, sources = build_report((output/"baseline_tracker.py").read_bytes())
    if (json.loads((output/"report.json").read_text()) != report
        or any((output/"source"/name).read_bytes() != data for name, data in sources.items())):
        raise ValueError("Report or archived source differs from reconstruction; use its original implementation/runtime.")
    return dict(verified=True, synthetic_tracker_crossing_runs=2*len(CASES),
                scope="Re-executed fixed detection cases in baseline and current tracker; no real camera or traffic performance validation.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path)
    mode.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        print(json.dumps(verify(args.verify), indent=2))
    else:
        report = run(args.output)
        print(json.dumps({name: {arm: {key: row[arm][key] for key in ("track_ids", "crossing_count")}
                                for arm in ("baseline", "corrected")} for name, row in report["cases"].items()}, indent=2))


if __name__ == "__main__":
    main()
