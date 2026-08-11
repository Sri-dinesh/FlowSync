"""
ROI Manager — Lane ROI definition, persistence, and vehicle-to-lane assignment.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..models.config import (
    DIRECTION_COLORS_BGR,
    LANE_KEYS,
    ROI_CONFIG_DIR,
    VEHICLE_QUEUE_WEIGHTS,
)
from ..models.schemas import (
    BoundingBox,
    LaneCounts,
    ROIConfig,
    ROIPolygon,
    VehicleDetection,
    VehicleTypeBreakdown,
    WeightedLaneCounts,
)
from ..utils.geometry import normalize_polygon_to_frame, point_in_polygon


class ROIManager:
    """
    Manages per-intersection, per-camera lane ROI polygons.

    ROIs define which pixels on the video frame correspond to which lane.
    Once defined for a camera, they're saved as JSON and reloaded on startup.

    Assignment logic: vehicle's bounding box BOTTOM CENTER falls inside ROI polygon.
    (Bottom center = vehicle's ground contact point — most accurate for lane assignment)
    """

    def __init__(self, roi_config_dir: str = ROI_CONFIG_DIR) -> None:
        self.roi_config_dir = Path(roi_config_dir)
        self.roi_config_dir.mkdir(parents=True, exist_ok=True)

    def _config_path(self, intersection_id: str, camera_id: str) -> Path:
        return self.roi_config_dir / f"{intersection_id}_{camera_id}.json"

    def load_config(
        self, intersection_id: str, camera_id: str
    ) -> Optional[ROIConfig]:
        """Load ROI config from disk. Returns None if not found."""
        path = self._config_path(intersection_id, camera_id)
        if not path.exists():
            return None
        try:
            with open(path) as f:
                data = json.load(f)
            return ROIConfig(**data)
        except Exception as e:
            print(f"[ROIManager] Failed to load config {path}: {e}")
            return None

    def save_config(self, config: ROIConfig) -> None:
        """Save ROI config to disk."""
        path = self._config_path(config.intersection_id, config.camera_id)
        with open(path, "w") as f:
            json.dump(config.model_dump(mode="json"), f, indent=2)

    def count_vehicles_per_lane(
        self,
        detection: VehicleDetection,
        roi_config: ROIConfig,
    ) -> Tuple[LaneCounts, WeightedLaneCounts, VehicleTypeBreakdown]:
        """
        Core method: for each detected vehicle, find which ROI its bottom-center falls in.

        Returns:
            - raw_counts: int count per lane
            - weighted_counts: weighted count per lane (vehicle type weight)
            - type_breakdown: per-class total vehicle counts
        """
        raw: Dict[str, int] = {lane: 0 for lane in LANE_KEYS}
        weighted: Dict[str, float] = {lane: 0.0 for lane in LANE_KEYS}
        type_counts: Dict[str, int] = {
            "bicycle": 0, "motorcycle": 0, "car": 0,
            "auto_rickshaw": 0, "van": 0, "bus": 0, "truck": 0,
        }

        for bbox in detection.bboxes:
            # Use bottom-center as ground contact point
            foot_x, foot_y = (bbox.x1 + bbox.x2) / 2, bbox.y2

            # Convert to relative coords for polygon matching
            rel_foot = (
                foot_x / detection.frame_width,
                foot_y / detection.frame_height,
            )

            # Find which ROI this vehicle falls into
            assigned_lane: Optional[str] = None
            for roi in roi_config.rois:
                if point_in_polygon(rel_foot, roi.vertices):
                    assigned_lane = roi.lane_id
                    break

            if assigned_lane and assigned_lane in raw:
                raw[assigned_lane] += 1
                weight = VEHICLE_QUEUE_WEIGHTS.get(bbox.class_name, 1.0)
                weighted[assigned_lane] += weight

            if bbox.class_name in type_counts:
                type_counts[bbox.class_name] += 1

        return (
            LaneCounts.from_dict(raw),
            WeightedLaneCounts.from_dict(weighted),
            VehicleTypeBreakdown(**type_counts),
        )

    def annotate_rois_on_frame(
        self, frame: np.ndarray, roi_config: ROIConfig
    ) -> np.ndarray:
        """Draw ROI polygons on frame with lane labels (for debug visualization)."""
        try:
            import cv2
        except ImportError:
            return frame

        annotated = frame.copy()
        h, w = frame.shape[:2]

        for roi in roi_config.rois:
            direction = roi.lane_id.split("_")[0]
            color = DIRECTION_COLORS_BGR.get(direction, (255, 255, 255))
            # Convert relative coords to pixel coords
            pts = np.array(
                [(int(x * w), int(y * h)) for x, y in roi.vertices],
                dtype=np.int32,
            )
            # Semi-transparent fill
            overlay = annotated.copy()
            cv2.fillPoly(overlay, [pts], color)
            cv2.addWeighted(overlay, 0.2, annotated, 0.8, 0, annotated)
            # Outline
            cv2.polylines(annotated, [pts], True, color, 2)
            # Label
            if len(pts) > 0:
                cx, cy = pts.mean(axis=0).astype(int)
                cv2.putText(
                    annotated,
                    roi.lane_id,
                    (cx - 30, cy),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    color,
                    1,
                    cv2.LINE_AA,
                )

        return annotated

    def list_configs(self) -> List[str]:
        """Return list of intersection_ids with saved configs."""
        ids = set()
        for f in self.roi_config_dir.glob("*.json"):
            parts = f.stem.rsplit("_", 1)
            if len(parts) >= 1:
                ids.add(parts[0])
        return sorted(ids)

    def validate_config(self, config: ROIConfig) -> List[str]:
        """
        Validate ROI config. Returns list of warnings/errors.
        """
        warnings = []
        defined_lanes = {roi.lane_id for roi in config.rois}

        # Check all 12 lanes defined
        for lane in LANE_KEYS:
            if lane not in defined_lanes:
                warnings.append(f"Missing ROI for lane: {lane}")

        # Check polygon validity (>= 3 vertices)
        for roi in config.rois:
            if len(roi.vertices) < 3:
                warnings.append(f"ROI {roi.lane_id} has fewer than 3 vertices")

        # Check for obviously out-of-bounds coords
        for roi in config.rois:
            for x, y in roi.vertices:
                if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
                    warnings.append(
                        f"ROI {roi.lane_id} has out-of-range vertex ({x:.2f}, {y:.2f})"
                    )

        return warnings
