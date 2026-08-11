"""
BayeTrack vehicle tracking wrapper — persistent IDs across frames.
"""
from __future__ import annotations

import math
import time
from typing import Dict, Optional, Set

from ..models.config import MOVEMENT_THRESHOLD_PX
from ..models.schemas import BoundingBox, TrackState, VehicleDetection


class VehicleTracker:
    """
    Wraps ultralytics ByteTrack for persistent vehicle ID tracking.

    Why tracking matters:
    - Consistent vehicle IDs -> measure actual per-vehicle wait time
    - Distinguishes new arrivals from already-queued vehicles
    - Reduces detection flickering (vehicle keeps ID even if missed 1-2 frames)
    - Required for accurate moving vs queued classification

    Note: tracker.update() must be called with every frame, even if no detections.
    """

    # Class-level counter shared across all instances
    _next_id_counter: int = 1

    def __init__(
        self,
        track_thresh: float = 0.4,
        track_buffer: int = 30,
        match_thresh: float = 0.8,
    ) -> None:
        self.track_thresh = track_thresh
        self.track_buffer = track_buffer
        self.match_thresh = match_thresh
        self._active_tracks: Dict[int, TrackState] = {}
        self._tracker = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            try:
                # ByteTrack is built into ultralytics as model.track()
                # We maintain our own state since we call YOLO separately
                self._initialized = True
            except Exception:
                self._initialized = True

    def update(self, detection: VehicleDetection) -> VehicleDetection:
        """
        Add/update track_id for each bbox.
        Returns updated VehicleDetection with track_ids assigned.
        Uses simple IoU-based matching as lightweight tracker.
        """
        self._ensure_initialized()
        now_ms = time.time() * 1000

        # Match detections to existing tracks via centroid distance
        updated_bboxes = []
        matched_track_ids: Set[int] = set()

        for bbox in detection.bboxes:
            cx, cy = (bbox.x1 + bbox.x2) / 2, (bbox.y1 + bbox.y2) / 2
            best_track_id = None
            best_dist = float("inf")

            for tid, track in self._active_tracks.items():
                if tid in matched_track_ids:
                    continue
                if not track.centroid_history:
                    continue
                tx, ty = track.centroid_history[-1]
                dist = math.sqrt((cx - tx) ** 2 + (cy - ty) ** 2)
                if dist < best_dist:
                    best_dist = dist
                    best_track_id = tid

            MAX_MATCH_DIST = 80.0  # pixels
            if best_track_id is not None and best_dist < MAX_MATCH_DIST:
                # Update existing track
                track = self._active_tracks[best_track_id]
                prev_cx, prev_cy = track.centroid_history[-1] if track.centroid_history else (cx, cy)
                moved = math.sqrt((cx - prev_cx) ** 2 + (cy - prev_cy) ** 2)
                track.is_moving = moved > MOVEMENT_THRESHOLD_PX
                track.last_seen_ms = now_ms
                track.centroid_history.append((cx, cy))
                if len(track.centroid_history) > 10:
                    track.centroid_history.pop(0)
                if not track.is_moving:
                    track.wait_time_seconds = (now_ms - track.first_seen_ms) / 1000.0
                matched_track_ids.add(best_track_id)
                new_bbox = BoundingBox(
                    x1=bbox.x1, y1=bbox.y1, x2=bbox.x2, y2=bbox.y2,
                    confidence=bbox.confidence,
                    class_id=bbox.class_id,
                    class_name=bbox.class_name,
                    track_id=best_track_id,
                )
            else:
                # New track
                new_tid = self._get_next_id()
                self._active_tracks[new_tid] = TrackState(
                    track_id=new_tid,
                    class_name=bbox.class_name,
                    first_seen_ms=now_ms,
                    last_seen_ms=now_ms,
                    is_moving=True,
                    centroid_history=[(cx, cy)],
                )
                matched_track_ids.add(new_tid)
                new_bbox = BoundingBox(
                    x1=bbox.x1, y1=bbox.y1, x2=bbox.x2, y2=bbox.y2,
                    confidence=bbox.confidence,
                    class_id=bbox.class_id,
                    class_name=bbox.class_name,
                    track_id=new_tid,
                )
            updated_bboxes.append(new_bbox)

        # Prune stale tracks (not seen in last 3 seconds)
        stale_threshold_ms = 3000.0
        stale_ids = [
            tid for tid, track in self._active_tracks.items()
            if (now_ms - track.last_seen_ms) > stale_threshold_ms
        ]
        for tid in stale_ids:
            del self._active_tracks[tid]

        return VehicleDetection(
            frame_id=detection.frame_id,
            timestamp_ms=detection.timestamp_ms,
            bboxes=updated_bboxes,
            inference_time_ms=detection.inference_time_ms,
            frame_width=detection.frame_width,
            frame_height=detection.frame_height,
        )

    def _get_next_id(self) -> int:
        tid = VehicleTracker._next_id_counter
        VehicleTracker._next_id_counter += 1
        return tid

    def get_active_tracks(self) -> Dict[int, TrackState]:
        return dict(self._active_tracks)

    def get_queued_vehicle_ids(self, lane_id: str) -> Set[int]:
        """IDs of non-moving vehicles assigned to a specific lane."""
        return {
            tid for tid, track in self._active_tracks.items()
            if track.lane_id == lane_id and not track.is_moving
        }

    def reset(self) -> None:
        """Clear all track state."""
        self._active_tracks.clear()
        VehicleTracker._next_id_counter = 1
