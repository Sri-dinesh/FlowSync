"""
Per-session metrics logger: FPS, detection stats, confidence distributions.
Thread-safe for use from async pipeline.
"""
from __future__ import annotations

import json
import threading
import time
from collections import defaultdict, deque
from typing import Any, Dict

from ..models.schemas import LaneCounts, VehicleDetection


class MetricsLogger:
    """Logs per-session detection metrics. Thread-safe."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._lock = threading.Lock()
        self._start_time = time.time()
        self._frame_times: deque = deque(maxlen=30)  # rolling 30 frames
        self._total_frames = 0
        self._class_counts: Dict[str, int] = defaultdict(int)
        self._class_confidences: Dict[str, list] = defaultdict(list)
        self._peak_queue_per_lane: Dict[str, int] = defaultdict(int)
        self._total_detections = 0
        self._inference_times: list = []

    def log_frame(
        self,
        detection: VehicleDetection,
        lane_counts: LaneCounts,
    ) -> None:
        """Log a single processed frame."""
        with self._lock:
            now = time.time()
            self._frame_times.append(now)
            self._total_frames += 1
            self._total_detections += len(detection.bboxes)
            self._inference_times.append(detection.inference_time_ms)

            for bbox in detection.bboxes:
                self._class_counts[bbox.class_name] += 1
                self._class_confidences[bbox.class_name].append(bbox.confidence)

            lane_dict = lane_counts.to_dict()
            for lane, count in lane_dict.items():
                if count > self._peak_queue_per_lane[lane]:
                    self._peak_queue_per_lane[lane] = count

    def get_fps(self) -> float:
        """Rolling FPS over last 30 frames."""
        with self._lock:
            times = list(self._frame_times)
            if len(times) < 2:
                return 0.0
            return (len(times) - 1) / (times[-1] - times[0] + 1e-9)

    def get_session_summary(self) -> Dict[str, Any]:
        """Returns comprehensive session summary."""
        with self._lock:
            elapsed = time.time() - self._start_time
            avg_fps = self._total_frames / elapsed if elapsed > 0 else 0.0
            avg_inference = (
                sum(self._inference_times) / len(self._inference_times)
                if self._inference_times else 0.0
            )
            avg_confidence: Dict[str, float] = {}
            for cls, confs in self._class_confidences.items():
                avg_confidence[cls] = sum(confs) / len(confs) if confs else 0.0

            return {
                "session_id": self.session_id,
                "total_frames": self._total_frames,
                "total_detections": self._total_detections,
                "duration_seconds": round(elapsed, 1),
                "avg_fps": round(avg_fps, 2),
                "avg_inference_ms": round(avg_inference, 1),
                "per_class_detection_counts": dict(self._class_counts),
                "avg_confidence_per_class": {k: round(v, 3) for k, v in avg_confidence.items()},
                "peak_queue_per_lane": dict(self._peak_queue_per_lane),
            }

    def export_to_json(self, path: str) -> None:
        """Export session summary to JSON file."""
        summary = self.get_session_summary()
        with open(path, "w") as f:
            json.dump(summary, f, indent=2)
