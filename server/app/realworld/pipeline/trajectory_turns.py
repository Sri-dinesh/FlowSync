"""Conservative retrospective turn labeling from continuous centroid tracks."""
from collections import Counter
from dataclasses import dataclass
import math

from ..models.calibration import contains
from ..models.crossings import StopLineCrossing
from ..models.trajectory_turns import TrajectoryObservation, TrajectoryTurn


@dataclass
class Pending:
    crossing: StopLineCrossing
    point: tuple[float, float]
    exit_id: str | None = None
    confirmations: int = 0


class TrajectoryTurns:
    def __init__(self, calibration):
        self.calibration = calibration
        self._pending = {}
        self._last_time = None
        self._last_frame = None
        self._last_event = None
        self.classified = self.unresolved = 0

    def update(self, detection, crossings):
        source_time = crossings.source_time_s
        t = source_time if source_time is not None and math.isfinite(source_time) and source_time >= 0 else None
        available = crossings.status == "available"
        result = TrajectoryObservation(status="available" if available else "observation_unavailable",
                                       calibration_sha256=self.calibration.sha256)
        def finish(tid, reason, exit_region=None):
            pending = self._pending.pop(tid)
            turn = exit_region.turns_from[pending.crossing.approach] if reason == "exit_confirmed" else None
            result.events.append(TrajectoryTurn(
                track_id=tid, crossing_frame_id=pending.crossing.frame_id, approach=pending.crossing.approach,
                calibration_sha256=self.calibration.sha256, frame_id=detection.frame_id, available_time_s=t,
                exit_id=exit_region.exit_id if exit_region else None, turn=turn, reason=reason))
            self.classified += turn is not None
            self.unresolved += turn is None

        if not available:
            for tid in list(self._pending):
                finish(tid, "observation_unavailable")
            self._last_frame = None
        else:
            if self._last_frame is not None and (detection.frame_id != self._last_frame+1 or t-self._last_time > result.max_gap_s):
                for tid in list(self._pending):
                    finish(tid, "timing_gap")
            self._last_time, self._last_frame = t, detection.frame_id
            multiplicity = Counter(box.track_id for box in detection.bboxes)
            points = {}
            for box in detection.bboxes:
                if (box.track_id is None or multiplicity[box.track_id] != 1
                    or not all(math.isfinite(v) for v in (box.x1, box.x2, box.y1, box.y2))
                    or box.x1 >= box.x2 or box.y1 >= box.y2):
                    continue
                point = ((box.x1+box.x2)/2, box.y2)
                if 0 <= point[0] <= detection.frame_width and 0 <= point[1] <= detection.frame_height:
                    points[box.track_id] = point
            for crossing in crossings.events:
                if crossing.track_id in points:
                    self._pending[crossing.track_id] = Pending(crossing, points[crossing.track_id])
            for tid, pending in list(self._pending.items()):
                if tid not in points:
                    finish(tid, "track_lost")
                    continue
                point = points[tid]
                if math.dist(pending.point, point) > result.max_displacement_px:
                    finish(tid, "implausible_displacement")
                    continue
                if t-pending.crossing.estimated_time_s > result.max_duration_s:
                    finish(tid, "timeout")
                    continue
                pending.point = point
                normalized = (point[0]/detection.frame_width, point[1]/detection.frame_height)
                exits = [region for region in self.calibration.exits if contains(region.vertices, normalized)]
                if len(exits) > 1:
                    finish(tid, "ambiguous_exit")
                elif exits:
                    region = exits[0]
                    if pending.crossing.approach not in region.turns_from:
                        finish(tid, "unmapped_exit", region)
                        continue
                    pending.confirmations = pending.confirmations+1 if pending.exit_id == region.exit_id else 1
                    pending.exit_id = region.exit_id
                    if pending.confirmations >= result.exit_confirmation_frames:
                        finish(tid, "exit_confirmed", region)
                else:
                    pending.exit_id, pending.confirmations = None, 0
        if result.events:
            self._last_event = result.events[-1]
        result.last_event = self._last_event
        result.pending_count = len(self._pending)
        result.classified_count, result.unresolved_count = self.classified, self.unresolved
        return result
