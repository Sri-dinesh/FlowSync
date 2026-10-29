"""
Centroid vehicle tracking — persistent IDs across frames.
"""
from __future__ import annotations

import math
from typing import Dict, Set

from ..models.config import MOVEMENT_THRESHOLD_PX
from ..models.schemas import BoundingBox, TrackState, VehicleDetection


class VehicleTracker:
    """Greedy nearest-centroid association with short track history and expiry.

    This implementation does not call Ultralytics ByteTrack. Pixel movement and
    time since first sighting are heuristics, not calibrated physical waiting.
    """

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
        self._next_id = 1
        self._last_time_s: float | None = None

    def update(self, detection: VehicleDetection, *, observation_time_s: float | None) -> VehicleDetection:
        """
        Add/update track_id for each bbox.
        Returns updated VehicleDetection with track_ids assigned.
        Use video-position seconds for files, monotonic receipt time for live
        sources. The clock must be fixed for this tracker instance. Missing or
        nonadvancing time breaks association; wall time is never substituted.
        """
        if (observation_time_s is None or not math.isfinite(observation_time_s) or observation_time_s < 0
            or (self._last_time_s is not None and observation_time_s <= self._last_time_s)):
            self._active_tracks.clear()
            return detection.model_copy(update={"bboxes": [box.model_copy(update={"track_id": None}) for box in detection.bboxes]})
        self._last_time_s = observation_time_s
        now_ms = observation_time_s * 1000
        # Expired tracks must not be resurrected by the next nearby detection.
        self._active_tracks = {tid: track for tid, track in self._active_tracks.items()
                               if now_ms-track.last_seen_ms <= 3000.0}

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

        return VehicleDetection(
            frame_id=detection.frame_id,
            timestamp_ms=detection.timestamp_ms,
            bboxes=updated_bboxes,
            inference_time_ms=detection.inference_time_ms,
            frame_width=detection.frame_width,
            frame_height=detection.frame_height,
            model_not_loaded=detection.model_not_loaded,
        )

    def _get_next_id(self) -> int:
        tid = self._next_id
        self._next_id += 1
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
        """Clear association and its clock without reusing this instance's IDs."""
        self._active_tracks.clear()
        self._last_time_s = None
