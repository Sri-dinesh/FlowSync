"""Exclusive approach-region occupancy from a frozen camera configuration."""
import math

from ..models.calibration import CameraCalibration, GeometryObservation, contains
from ..models.schemas import VehicleDetection


def assign_approaches(detection: VehicleDetection, calibration: CameraCalibration):
    status = "matched"
    if (detection.frame_width, detection.frame_height) != (calibration.frame_width, calibration.frame_height):
        status = "frame_size_mismatch"
    elif detection.model_not_loaded:
        status = "detector_unavailable"
    counts = {region.approach: 0 for region in calibration.approaches}
    assignments = []
    ambiguous = 0
    for box in detection.bboxes:
        matches = []
        if status == "matched" and all(math.isfinite(v) for v in (box.x1, box.x2, box.y1, box.y2)) and box.x1 < box.x2 and box.y1 < box.y2:
            point = ((box.x1+box.x2)/2/detection.frame_width, box.y2/detection.frame_height)
            if 0 <= point[0] <= 1 and 0 <= point[1] <= 1:
                matches = [region.approach for region in calibration.approaches if contains(region.vertices, point)]
        approach = matches[0] if len(matches) == 1 else None
        assignments.append(approach)
        if approach is not None:
            counts[approach] += 1
        ambiguous += len(matches) > 1
    assigned = sum(counts.values())
    return assignments, GeometryObservation(
        status=status, calibration_sha256=calibration.sha256,
        configured_approaches=tuple(counts), approach_counts=counts,
        assigned_boxes=assigned, unassigned_boxes=len(assignments)-assigned, ambiguous_boxes=ambiguous,
    )


def draw_calibration(frame, calibration: CameraCalibration):
    import cv2
    import numpy as np

    output = frame.copy()
    height, width = frame.shape[:2]
    if (width, height) != (calibration.frame_width, calibration.frame_height):
        return output
    for region in calibration.approaches:
        points = np.array([(round(x*width), round(y*height)) for x, y in region.vertices], dtype=np.int32)
        cv2.polylines(output, [points], True, (255, 200, 50), 2)
        start, end = [(round(x*width), round(y*height)) for x, y in region.stop_line]
        cv2.line(output, start, end, (0, 180, 255), 3)
        x, y = points.mean(axis=0).astype(int)
        cv2.putText(output, region.approach, (x, y), cv2.FONT_HERSHEY_SIMPLEX, .5, (255, 255, 255), 1)
    return output
