"""Conservative finite-segment crossings from consecutive tracked observations."""
import math
from collections import Counter
from dataclasses import dataclass

from ..models.calibration import CameraCalibration, cross
from ..models.crossings import CrossingObservation, StopLineCrossing


@dataclass(frozen=True)
class Anchor:
    approach: str
    point: tuple[float, float]
    time_s: float
    frame_id: int


class StopLineCrossings:
    def __init__(self, calibration: CameraCalibration):
        self.calibration = calibration
        self._anchors = {}
        self._emitted = set()
        self._last_time = None
        self._last_frame = None
        self._last_event = None
        self.counts = {region.approach: 0 for region in calibration.approaches}
        self.lines = {}
        for region in calibration.approaches:
            a, b = [self.pixel(p) for p in region.stop_line]
            centre = self.pixel(tuple(sum(p[i] for p in region.vertices)/len(region.vertices) for i in (0, 1)))
            sign = 1 if cross(a, b, centre) > 0 else -1
            self.lines[region.approach] = (a, b, sign, math.dist(a, b))

    def pixel(self, point):
        return point[0]*self.calibration.frame_width, point[1]*self.calibration.frame_height

    def update(self, detection, assignments, geometry, source_time_s):
        status = "available"
        if geometry.status != "matched":
            status = "geometry_unavailable"
        elif source_time_s is None or not math.isfinite(source_time_s) or source_time_s < 0 or (
            self._last_time is not None and source_time_s <= self._last_time
        ):
            status = "source_timing_unavailable"
        result = CrossingObservation(status=status, source_time_s=source_time_s if source_time_s is not None and math.isfinite(source_time_s) else None,
                                     counts=dict(self.counts), last_event=self._last_event)
        if status != "available":
            self._anchors.clear()
            self._last_frame = None
            return result
        if self._last_frame is not None and (detection.frame_id != self._last_frame+1 or source_time_s-self._last_time > result.max_gap_s):
            self._anchors.clear()
        self._last_time, self._last_frame = source_time_s, detection.frame_id
        multiplicity = Counter(box.track_id for box in detection.bboxes)
        next_anchors = {}
        for box, approach in zip(detection.bboxes, assignments):
            tid = box.track_id
            if tid is None or multiplicity[tid] != 1 or not all(math.isfinite(v) for v in (box.x1, box.x2, box.y1, box.y2)) or box.x1 >= box.x2 or box.y1 >= box.y2:
                continue
            point = ((box.x1+box.x2)/2, box.y2)
            if not (0 <= point[0] <= self.calibration.frame_width and 0 <= point[1] <= self.calibration.frame_height):
                continue
            anchor = self._anchors.get(tid)
            if anchor and source_time_s-anchor.time_s <= result.max_gap_s and math.dist(point, anchor.point) <= result.max_displacement_px:
                a, b, sign, length = self.lines[anchor.approach]
                distance = sign*cross(a, b, point)/length
                if distance < -result.deadband_px:
                    previous_distance = sign*cross(a, b, anchor.point)/length
                    fraction = previous_distance/(previous_distance-distance)
                    hit = tuple(anchor.point[i]+fraction*(point[i]-anchor.point[i]) for i in (0, 1))
                    along = sum((hit[i]-a[i])*(b[i]-a[i]) for i in (0, 1))/length
                    key = (tid, anchor.approach)
                    if result.deadband_px < along < length-result.deadband_px and key not in self._emitted:
                        self._emitted.add(key)
                        self.counts[anchor.approach] += 1
                        result.events.append(StopLineCrossing(
                            track_id=tid, approach=anchor.approach, calibration_sha256=self.calibration.sha256,
                            previous_frame_id=anchor.frame_id, frame_id=detection.frame_id,
                            time_interval_s=(anchor.time_s, source_time_s),
                            estimated_time_s=anchor.time_s+fraction*(source_time_s-anchor.time_s),
                            point=(hit[0]/self.calibration.frame_width, hit[1]/self.calibration.frame_height),
                        ))
                elif abs(distance) <= result.deadband_px:
                    next_anchors[tid] = anchor
            if approach is not None:
                a, b, sign, length = self.lines[approach]
                if sign*cross(a, b, point)/length > result.deadband_px:
                    next_anchors[tid] = Anchor(approach, point, source_time_s, detection.frame_id)
        self._anchors = next_anchors
        result.counts = dict(self.counts)
        if result.events:
            self._last_event = result.events[-1]
        result.last_event = self._last_event
        return result
