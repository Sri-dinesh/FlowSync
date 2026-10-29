"""One-to-one evaluation of recorded discharges against independently supplied labels."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
import pydantic

from server.app.realworld.models.calibration import CameraCalibration, Direction
from server.app.realworld.models.crossings import CrossingObservation, StopLineCrossing

ROOT = Path(__file__).resolve().parents[2]
Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Time = Annotated[float, Field(ge=0, allow_inf_nan=False, strict=True)]
Identifier = Annotated[str, Field(min_length=1, max_length=200)]
MAX_MATCH_CELLS = 2_000_000


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Protocol(StrictModel):
    schema_version: Literal["crossing_evaluation_v1"]
    protocol_id: Identifier
    match_tolerance_s: Annotated[float, Field(ge=0, le=5, allow_inf_nan=False, strict=True)]


class Window(StrictModel):
    window_id: Identifier
    approach: Direction
    start_s: Time
    end_s: Time
    exhaustive: Literal[True]


class Label(StrictModel):
    event_id: Identifier
    approach: Direction
    time_s: Time


class Annotations(StrictModel):
    schema_version: Literal["crossing_annotations_v1"]
    video_sha256: Hash
    calibration_sha256: Hash
    origin: Literal["human", "synthetic_fixture"]
    split: Literal["calibration", "development", "held_out"]
    annotation_method: Annotated[str, Field(min_length=10)]
    time_resolution_s: Annotated[float, Field(gt=0, allow_inf_nan=False, strict=True)]
    windows: Annotated[list[Window], Field(min_length=1)]
    events: list[Label]

    @model_validator(mode="after")
    def valid_windows(self):
        if len({w.window_id for w in self.windows}) != len(self.windows) or len({e.event_id for e in self.events}) != len(self.events):
            raise ValueError("Window IDs and annotation event IDs must be unique.")
        for i, window in enumerate(self.windows):
            if window.end_s <= window.start_s:
                raise ValueError("Each scored window needs positive duration.")
            if any(other.approach == window.approach and max(window.start_s, other.start_s) < min(window.end_s, other.end_s)
                   for other in self.windows[i+1:]):
                raise ValueError("Scored windows on the same approach must not overlap.")
        for event in self.events:
            if sum(inside(event.approach, event.time_s, window) for window in self.windows) != 1:
                raise ValueError("Every label must belong to exactly one scored window.")
        return self


class RecordedFrame(BaseModel):
    frame_id: int
    crossing_observation: CrossingObservation | None = None


class Session(BaseModel):
    session_id: Identifier
    source_video_sha256: Hash
    calibration: CameraCalibration
    calibration_sha256: Hash
    frames: list[RecordedFrame]
    stop_line_crossings: list[StopLineCrossing]


def inside(approach, time_s, window):
    return approach == window.approach and window.start_s <= time_s < window.end_s


def match_events(predictions, labels, tolerance):
    """Maximum-cardinality monotone matching, then minimum absolute time error."""
    predicted = sorted(predictions, key=lambda row: (row[1], row[0]))
    truth = sorted(labels, key=lambda row: (row[1], row[0]))
    n, m = len(predicted), len(truth)
    if (n+1)*(m+1) > MAX_MATCH_CELLS:
        raise ValueError("Matching budget exceeded; use shorter predeclared annotation windows.")
    choices = [bytearray(m+1) for _ in range(n+1)]
    previous = [(0, 0.)]*(m+1)
    for i in range(1, n+1):
        current = [(0, 0.)]*(m+1)
        for j in range(1, m+1):
            options = [(previous[j][0], previous[j][1], 0), (current[j-1][0], current[j-1][1], 1)]
            error = abs(predicted[i-1][1]-truth[j-1][1])
            if error <= tolerance:
                options.append((previous[j-1][0]+1, previous[j-1][1]-error, 2))
            best = max(options)
            current[j], choices[i][j] = best[:2], best[2]
        previous = current
    matched = []
    i, j = n, m
    while i and j:
        choice = choices[i][j]
        if choice == 2:
            matched.append((predicted[i-1][0], truth[j-1][0], predicted[i-1][1]-truth[j-1][1]))
            i, j = i-1, j-1
        elif choice == 1:
            j -= 1
        else:
            i -= 1
    return list(reversed(matched))


def metrics(tp, fp, fn, signed_errors):
    return dict(true_positive=tp, false_positive=fp, false_negative=fn,
                precision=tp/(tp+fp) if tp+fp else None, recall=tp/(tp+fn) if tp+fn else None,
                f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None,
                matched_timing_mae_s=statistics.mean(map(abs, signed_errors)) if signed_errors else None,
                matched_timing_bias_s=statistics.mean(signed_errors) if signed_errors else None)


def check_session(session):
    if session.calibration.sha256 != session.calibration_sha256:
        raise ValueError("Recorded calibration hash mismatch.")
    counts = {region.approach: 0 for region in session.calibration.approaches}
    flattened, times, clock_times, seen = [], {}, {}, set()
    unavailable = 0
    previous_frame_id = -1
    last_source_time = None
    for frame in session.frames:
        observation = frame.crossing_observation
        if observation is None:  # Includes the end-of-video status record.
            continue
        if frame.frame_id <= previous_frame_id:
            raise ValueError("Crossing frames must have strictly increasing IDs.")
        previous_frame_id = frame.frame_id
        t = observation.source_time_s
        clock_valid = (t is not None and math.isfinite(t) and t >= 0
                       and (last_source_time is None or t > last_source_time))
        if observation.status in ("available", "geometry_unavailable") and clock_valid:
            clock_times[frame.frame_id] = t
            last_source_time = t
        if observation.status == "available":
            if not clock_valid:
                raise ValueError("Available frames require advancing finite source times.")
            times[frame.frame_id] = t
        else:
            unavailable += 1
            if observation.events:
                raise ValueError("Unavailable observations cannot contain crossing events.")
        for event in observation.events:
            t0, t1 = event.time_interval_s
            key = (event.track_id, event.approach)
            if (event.approach not in counts or key in seen or event.calibration_sha256 != session.calibration_sha256
                or event.frame_id != frame.frame_id or event.previous_frame_id >= frame.frame_id
                or times.get(event.previous_frame_id) != t0 or times.get(frame.frame_id) != t1
                or not t0 < event.estimated_time_s < t1):
                raise ValueError("Crossing identity, provenance or bracketing frame times are inconsistent.")
            seen.add(key)
            counts[event.approach] += 1
            flattened.append(event)
        if observation.counts != counts:
            raise ValueError("Cumulative crossing counts do not reconstruct from frame events.")
    if flattened != session.stop_line_crossings or not clock_times:
        raise ValueError("Session events differ from frame events, or source timing is absent.")
    timestamps = list(clock_times.values())
    return dict(available_timing_frames=len(clock_times), available_crossing_frames=len(times), unavailable_crossing_frames=unavailable,
                first_source_time_s=timestamps[0], last_source_time_s=timestamps[-1],
                max_available_timestamp_gap_s=max((b-a for a,b in zip(timestamps,timestamps[1:])),default=None))


def evaluate(session, annotations, protocol, video_sha256):
    if session.source_video_sha256 != video_sha256 or annotations.video_sha256 != video_sha256:
        raise ValueError("Video bytes do not match the session and annotation identities.")
    if annotations.calibration_sha256 != session.calibration_sha256:
        raise ValueError("Annotations target a different calibration.")
    coverage = check_session(session)
    configured = {region.approach for region in session.calibration.approaches}
    per_window, matched, extras, misses, scored_predictions = [], [], [], [], set()
    for window in annotations.windows:
        if (window.approach not in configured or window.start_s < coverage["first_source_time_s"]
            or window.end_s > coverage["last_source_time_s"]):
            raise ValueError("Scored windows must lie within configured approaches and recorded source-time extent.")
        predicted = [(i, event.estimated_time_s) for i, event in enumerate(session.stop_line_crossings)
                     if inside(event.approach, event.estimated_time_s, window)]
        labels = [(e.event_id, e.time_s) for e in annotations.events if inside(e.approach, e.time_s, window)]
        pairs = match_events(predicted, labels, protocol.match_tolerance_s)
        used_p, used_l = {p for p, _, _ in pairs}, {l for _, l, _ in pairs}
        extra = [i for i, _ in predicted if i not in used_p]
        missed = [i for i, _ in labels if i not in used_l]
        matched.extend(dict(window_id=window.window_id, approach=window.approach,
                            prediction_index=p, annotation_id=l, signed_timing_error_s=e) for p, l, e in pairs)
        extras.extend(extra)
        misses.extend(missed)
        scored_predictions.update(i for i, _ in predicted)
        per_window.append(dict(window_id=window.window_id, approach=window.approach,
                               **metrics(len(pairs), len(extra), len(missed), [e for _, _, e in pairs])))
    overall = metrics(len(matched), len(extras), len(misses), [m["signed_timing_error_s"] for m in matched])
    return dict(schema_version="crossing_evaluation_v1", complete=True, protocol=protocol.model_dump(),
                annotation_origin=annotations.origin, declared_split=annotations.split,
                split_independence_verified=False, annotation_method=annotations.annotation_method,
                annotation_time_resolution_s=annotations.time_resolution_s, coverage=coverage,
                scored_approach_seconds=sum(w.end_s-w.start_s for w in annotations.windows),
                metrics=overall, per_window=per_window, matches=matched,
                unmatched_prediction_indices=extras, unmatched_annotation_ids=misses,
                unscored_prediction_indices=sorted(set(range(len(session.stop_line_crossings)))-scored_predictions),
                publication_ready=False, policy_promoted=False, physical_actuation=False,
                scope="Approach/time event agreement within exhaustive labeled windows; not object identity, YOLO accuracy or control performance.")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def build_report(inputs, video_hash):
    report = evaluate(Session.model_validate_json(inputs["session.json"]),
                      Annotations.model_validate_json(inputs["annotations.json"]),
                      Protocol.model_validate_json(inputs["protocol.json"]), video_hash)
    sources = {name: (ROOT/name).read_bytes() for name in (
        "research/cv/evaluate_crossings.py", "server/app/realworld/models/calibration.py",
        "server/app/realworld/models/crossings.py")}
    report["input_sha256"] = {name: digest(data) for name, data in inputs.items()}
    report["video_sha256"] = video_hash
    report["source_sha256"] = {name: digest(data) for name, data in sources.items()}
    report["python_version"] = sys.version
    report["pydantic_version"] = pydantic.__version__
    return report, sources


def video_digest(video_path):
    with video_path.open("rb") as video:
        return hashlib.file_digest(video, "sha256").hexdigest()


def run(session_path, annotations_path, protocol_path, video_path, output):
    inputs = {name: path.read_bytes() for name, path in (
        ("session.json", session_path), ("annotations.json", annotations_path), ("protocol.json", protocol_path))}
    report, sources = build_report(inputs, video_digest(video_path))
    output.mkdir(parents=True, exist_ok=False)
    for name, data in inputs.items():
        (output/name).write_bytes(data)
    for name, data in sources.items():
        target = output/"source"/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (output/"report.json").write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    return report


def verify(output, video_path):
    report = json.loads((output/"report.json").read_text())
    inputs = {name: (output/name).read_bytes() for name in ("session.json", "annotations.json", "protocol.json")}
    rebuilt, sources = build_report(inputs, video_digest(video_path))
    if report != rebuilt or any((output/"source"/name).read_bytes() != data for name, data in sources.items()):
        raise ValueError("Report, inputs or source do not reconstruct; historical reports require their archived implementation/runtime.")
    return dict(verified=True, scope="Stored-event consistency, hashes and annotation-matching reconstruction; no trajectory rerun.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("session", "annotations", "protocol", "output", "verify"):
        parser.add_argument(f"--{name}", type=Path)
    parser.add_argument("--video", type=Path, required=True)
    args = parser.parse_args()
    if args.verify:
        if any((args.session, args.annotations, args.protocol, args.output)):
            parser.error("--verify accepts only --video alongside it.")
        print(json.dumps(verify(args.verify, args.video), indent=2))
        return
    if not all((args.session, args.annotations, args.protocol, args.output)):
        parser.error("Evaluation requires --session, --annotations, --protocol and --output.")
    report = run(args.session, args.annotations, args.protocol, args.video, args.output)
    print(json.dumps({"complete": report["complete"], "annotation_origin": report["annotation_origin"],
                      "metrics": report["metrics"], "publication_ready": False}, indent=2))


if __name__ == "__main__":
    main()
