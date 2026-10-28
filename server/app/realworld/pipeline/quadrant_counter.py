"""Exclusive image-direction proxies, not calibrated road or turn measurements."""
from __future__ import annotations

import math
from typing import Dict, Optional

from ..models.config import LANE_KEYS
from ..models.schemas import BoundingBox, VehicleDetection


def image_direction(bbox: BoundingBox, width: int, height: int) -> Optional[str]:
    """Assign at most one direction; centre/diagonal ties remain unassigned."""
    if width <= 0 or height <= 0:
        raise ValueError("Frame dimensions must be positive")
    x, y = bbox.bottom_center
    if not all(math.isfinite(v) for v in (bbox.x1, bbox.x2, bbox.y1, bbox.y2)):
        return None
    if bbox.width <= 0 or bbox.height <= 0 or not (0 <= x <= width and 0 <= y <= height):
        return None
    dx, dy = x/width-.5, y/height-.5
    if math.isclose(abs(dx), abs(dy), abs_tol=1e-9, rel_tol=0):
        return None
    if abs(dy) > abs(dx):
        return "north" if dy < 0 else "south"
    return "west" if dx < 0 else "east"


class QuadrantCounter:
    """Compatibility slots use *_straight keys; turning movements are unknown.

    An image direction need not coincide with a physical road approach. This
    heuristic cannot replace a configured movement ROI or infer a signal phase.
    """

    def count(self, detection: VehicleDetection) -> Dict[str, int]:
        counts = {k: 0 for k in LANE_KEYS}
        if detection.model_not_loaded:
            return counts
        for bbox in detection.bboxes:
            direction = image_direction(bbox, detection.frame_width, detection.frame_height)
            if direction is not None:
                counts[f"{direction}_straight"] += 1
        return counts

    def count_directions_only(self, detection: VehicleDetection) -> Dict[str, int]:
        counts = self.count(detection)
        return {d: counts[f"{d}_straight"] for d in ("north", "south", "east", "west")}
