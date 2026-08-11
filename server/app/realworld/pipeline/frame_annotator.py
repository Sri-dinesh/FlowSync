"""
FrameAnnotator — Draw YOLO bboxes, ROI polygons, lane counts, and signal decisions on frames.
"""
from __future__ import annotations

import base64
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..models.config import DIRECTION_COLORS_BGR, LANE_KEYS
from ..models.schemas import CCTVFrame, LaneCounts, ROIConfig, VehicleDetection


class FrameAnnotator:
    """
    Annotates video frames with:
    - Bounding boxes per vehicle (color-coded by class)
    - Vehicle class label + confidence score
    - Track ID (if tracking enabled)
    - ROI polygon outlines with lane labels
    - Lane queue count overlay
    - Signal decision badge (current phase + DQN recommendation)
    """

    # Color scheme (BGR for OpenCV)
    CLASS_COLORS: Dict[str, Tuple[int, int, int]] = {
        "bicycle":      (0, 165, 255),
        "motorcycle":   (255, 255, 0),
        "car":          (0, 255, 0),
        "auto_rickshaw": (255, 0, 255),
        "van":          (0, 200, 255),
        "bus":          (255, 0, 0),
        "truck":        (0, 140, 255),
    }

    PHASE_NAMES = {
        0: "NS_STR",
        1: "EW_STR",
        2: "NS_LEFT",
        3: "EW_LEFT",
    }

    def annotate(
        self,
        frame: np.ndarray,
        detection: VehicleDetection,
        roi_config: Optional[ROIConfig] = None,
        lane_counts: Optional[LaneCounts] = None,
        cctv_frame: Optional[CCTVFrame] = None,
    ) -> np.ndarray:
        """Apply all annotations. Returns annotated frame."""
        try:
            import cv2
        except ImportError:
            return frame

        annotated = frame.copy()

        # Draw ROI polygons first (behind bboxes)
        if roi_config is not None:
            annotated = self._draw_roi_overlays(annotated, roi_config, cv2)

        # Draw bounding boxes
        for bbox in detection.bboxes:
            annotated = self._draw_bbox(annotated, bbox, cv2)

        # Draw lane queue HUD
        if lane_counts is not None:
            annotated = self._draw_queue_hud(annotated, lane_counts, cv2)

        # Draw signal decision badge
        if cctv_frame is not None:
            annotated = self._draw_signal_badge(
                annotated,
                cctv_frame.signal_phase_name,
                cctv_frame.q_values,
                cctv_frame.confidence_pct,
                cv2,
            )

        return annotated

    def encode_frame_b64(self, frame: np.ndarray, quality: int = 75) -> str:
        """Encode annotated frame to base64 JPEG for WebSocket streaming."""
        try:
            import cv2
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, quality]
            _, buffer = cv2.imencode(".jpg", frame, encode_params)
            return base64.b64encode(buffer.tobytes()).decode("utf-8")
        except Exception:
            return ""

    def _draw_bbox(self, frame: np.ndarray, bbox, cv2) -> np.ndarray:
        """Draw single bounding box with label."""
        color = self.CLASS_COLORS.get(bbox.class_name, (200, 200, 200))
        x1, y1, x2, y2 = int(bbox.x1), int(bbox.y1), int(bbox.x2), int(bbox.y2)

        # Box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # Label background
        label = f"{bbox.class_name} {bbox.confidence:.0%}"
        if bbox.track_id is not None:
            label += f" #{bbox.track_id}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
        cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)

        # Label text
        cv2.putText(
            frame, label,
            (x1 + 2, y1 - 4),
            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1, cv2.LINE_AA,
        )
        return frame

    def _draw_roi_overlays(self, frame: np.ndarray, roi_config: ROIConfig, cv2) -> np.ndarray:
        """Draw ROI polygons with lane labels."""
        h, w = frame.shape[:2]
        for roi in roi_config.rois:
            direction = roi.lane_id.split("_")[0]
            color = DIRECTION_COLORS_BGR.get(direction, (255, 255, 255))
            pts = np.array(
                [(int(x * w), int(y * h)) for x, y in roi.vertices],
                dtype=np.int32,
            )
            overlay = frame.copy()
            cv2.fillPoly(overlay, [pts], color)
            cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)
            cv2.polylines(frame, [pts], True, color, 1)
        return frame

    def _draw_signal_badge(
        self,
        frame: np.ndarray,
        phase_name: str,
        q_values: List[float],
        confidence_pct: float,
        cv2,
    ) -> np.ndarray:
        """Draw signal decision badge in bottom-right corner."""
        h, w = frame.shape[:2]
        badge_w, badge_h = 160, 80
        bx, by = w - badge_w - 10, h - badge_h - 10

        # Background
        overlay = frame.copy()
        cv2.rectangle(overlay, (bx, by), (bx + badge_w, by + badge_h), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        cv2.rectangle(frame, (bx, by), (bx + badge_w, by + badge_h), (0, 255, 100), 1)

        # Phase name
        cv2.putText(
            frame, f"DQN: {phase_name}",
            (bx + 5, by + 16),
            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 100), 1, cv2.LINE_AA,
        )
        # Confidence
        cv2.putText(
            frame, f"Conf: {confidence_pct:.0f}%",
            (bx + 5, by + 32),
            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (200, 200, 200), 1, cv2.LINE_AA,
        )
        # Q-value mini bars
        if q_values:
            max_q = max(q_values) if max(q_values) > 0 else 1.0
            bar_w = (badge_w - 10) // len(q_values)
            for i, q in enumerate(q_values):
                bh = int((q / max_q) * 30) if max_q > 0 else 0
                bar_color = (0, 200, 80) if i == q_values.index(max(q_values)) else (100, 100, 100)
                bx_i = bx + 5 + i * bar_w
                cv2.rectangle(frame, (bx_i, by + badge_h - 5 - bh), (bx_i + bar_w - 2, by + badge_h - 5), bar_color, -1)

        return frame

    def _draw_queue_hud(
        self, frame: np.ndarray, lane_counts: LaneCounts, cv2
    ) -> np.ndarray:
        """Draw lane queue count HUD in top-left corner."""
        counts = lane_counts.to_dict()
        active = [(lane, cnt) for lane, cnt in counts.items() if cnt > 0]

        if not active:
            return frame

        line_h = 14
        hud_h = len(active) * line_h + 8
        hud_w = 170

        overlay = frame.copy()
        cv2.rectangle(overlay, (5, 5), (5 + hud_w, 5 + hud_h), (10, 10, 10), -1)
        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)

        for i, (lane, cnt) in enumerate(active):
            color = (0, 255, 80) if cnt <= 3 else (0, 200, 255) if cnt <= 6 else (0, 50, 255)
            cv2.putText(
                frame,
                f"{lane}: {cnt}",
                (10, 5 + (i + 1) * line_h),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, color, 1, cv2.LINE_AA,
            )
        return frame

    def annotate_simple(
        self,
        frame: np.ndarray,
        detection: "VehicleDetection",
    ) -> np.ndarray:
        """
        Draws only YOLO bounding boxes on the frame (no ROI polygons, no phase info).
        Used by the simplified pipeline that works without any ROI configuration.
        """
        try:
            import cv2
        except ImportError:
            return frame

        annotated = frame.copy()
        for bbox in detection.bboxes:
            color = self.CLASS_COLORS.get(bbox.class_name, (0, 255, 128))
            x1, y1, x2, y2 = int(bbox.x1), int(bbox.y1), int(bbox.x2), int(bbox.y2)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            label = f"{bbox.class_name} {bbox.confidence:.0%}"
            cv2.putText(
                annotated, label,
                (x1, max(y1 - 5, 15)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA,
            )
        return annotated
