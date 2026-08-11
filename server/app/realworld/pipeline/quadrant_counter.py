"""
QuadrantCounter — Full-frame vehicle counting without ROI polygons.

Divides the video frame into 4 quadrants (North/South/East/West) based
on vehicle bounding-box bottom-center points. This replaces the ROI-polygon
approach so zero configuration is needed before processing a video.

Quadrant mapping:
  Top half    (y < 0.5) → North
  Bottom half (y >= 0.5) → South
  Left half   (x < 0.5) → West
  Right half  (x >= 0.5) → East

Vehicles whose bottom-center is near the frame center (within CENTER_BAND)
are split across both their N/S and E/W quadrants.
"""
from __future__ import annotations

from typing import Dict

from ..models.schemas import VehicleDetection

# Vehicles within ±CENTER_BAND of the frame center are assigned to both adjacent dirs
CENTER_BAND = 0.15

LANE_KEYS = [
    "north_straight", "north_left", "north_right",
    "south_straight", "south_left", "south_right",
    "east_straight", "east_left", "east_right",
    "west_straight", "west_left", "west_right",
]


class QuadrantCounter:
    """
    Maps YOLO bounding boxes to directional lane counts using frame quadrants.

    All vehicles are assigned to the ``_straight`` movement for their direction.
    Left/right movements are not inferred from a static camera without ROI.
    """

    def count(self, detection: VehicleDetection) -> Dict[str, int]:
        """
        Count vehicles per lane key using frame-quadrant heuristic.

        Args:
            detection: VehicleDetection from YOLO inference.

        Returns:
            dict with all 12 lane keys (north_straight, north_left, …)
            with integer vehicle counts. Only *_straight keys will be non-zero.
        """
        counts: Dict[str, int] = {k: 0 for k in LANE_KEYS}

        if detection.model_not_loaded or not detection.bboxes:
            return counts

        fw = detection.frame_width or 1
        fh = detection.frame_height or 1

        for bbox in detection.bboxes:
            # Use bottom-center as the vehicle's ground contact point
            cx = ((bbox.x1 + bbox.x2) / 2) / fw  # normalised [0, 1]
            cy = bbox.y2 / fh                      # bottom edge, normalised [0, 1]

            near_h_center = abs(cy - 0.5) < CENTER_BAND
            near_v_center = abs(cx - 0.5) < CENTER_BAND

            # Vertical (N/S) assignment
            if cy < 0.5:
                counts["north_straight"] += 1
                if near_h_center:
                    counts["south_straight"] += 1
            else:
                counts["south_straight"] += 1
                if near_h_center:
                    counts["north_straight"] += 1

            # Horizontal (E/W) assignment
            if cx < 0.5:
                counts["west_straight"] += 1
                if near_v_center:
                    counts["east_straight"] += 1
            else:
                counts["east_straight"] += 1
                if near_v_center:
                    counts["west_straight"] += 1

        return counts

    def count_directions_only(self, detection: VehicleDetection) -> Dict[str, int]:
        """
        Simplified count returning just 4 direction totals (no turn breakdown).

        Returns:
            dict: {"north": N, "south": N, "east": N, "west": N}
        """
        counts = self.count(detection)
        return {
            "north": counts["north_straight"],
            "south": counts["south_straight"],
            "east":  counts["east_straight"],
            "west":  counts["west_straight"],
        }
