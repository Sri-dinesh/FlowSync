"""
CCTVPipeline — Main orchestrator. Ties all pipeline steps into a single async loop.
Runs at PIPELINE_FPS (2Hz), handling video frames, YOLO detection, optional configured
approach occupancy or image-direction proxies, annotation, and WebSocket broadcast.

Each box has at most one assignment. Configured geometry measures region occupancy,
not turns or stopped queues. The output contract marks learned control unavailable.

Detection confidence monitoring applies only to displayed counts.
When rolling average detection confidence drops below CONFIDENCE_FALLBACK_THRESHOLD
the pipeline falls back to last-known-good lane counts and logs a warning.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Any, Awaitable, Callable, Deque, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

from ..models.config import PIPELINE_FPS
from ..models.calibration import CameraCalibration
from ..models.signal_timeline import SignalTimeline, SignalTimelineReader
from ..models.schemas import (
    CCTVFrame,
    CameraObservationContract,
    LaneCounts,
    VehicleTypeBreakdown,
    WeightedLaneCounts,
)
from .frame_annotator import FrameAnnotator
from .quadrant_counter import QuadrantCounter, image_direction
from .camera_geometry import assign_approaches, draw_calibration
from .stop_line_crossings import StopLineCrossings
from .trajectory_turns import TrajectoryTurns
from .vehicle_tracker import VehicleTracker
from .video_processor import VideoProcessor
from .yolo_detector import YOLODetector
from ..utils.temporal_smoother import TemporalSmoother
from ..utils.metrics_logger import MetricsLogger


class CCTVPipeline:
    """
    Orchestrates the full real-world processing pipeline at PIPELINE_FPS (2Hz).

    Pipeline steps per tick:
    1. Extract frame from video source (VideoProcessor)
    2. Run YOLO detection (YOLODetector) via asyncio.to_thread()
    3. Update persistent vehicle tracks (VehicleTracker) & log timestamped arrival events
    4. Count vehicles per direction (QuadrantCounter)
    5. Apply temporal smoothing (TemporalSmoother)
    6. Annotate frame with bboxes (FrameAnnotator) — base64 encode
    7. Emit CCTVFrame via callback (for WebSocket broadcast)
    8. Log metrics (MetricsLogger)
    """

    def __init__(
        self,
        video_processor: VideoProcessor,
        yolo_detector: YOLODetector,
        on_frame: Callable[[CCTVFrame], Awaitable[None]],
        on_progress: Optional[Callable[[Dict], Awaitable[None]]] = None,
        on_arrival: Optional[Callable[[Dict], Awaitable[None]]] = None,
        session_id: str = "session_001",
        annotate_frames: bool = True,
        calibration: Optional[CameraCalibration] = None,
        signal_timeline: Optional[SignalTimeline] = None,
    ) -> None:
        self.video_processor = video_processor
        self.yolo_detector = yolo_detector
        self.on_frame = on_frame
        self.on_progress = on_progress
        self.on_arrival = on_arrival
        self.session_id = session_id
        self.annotate_frames = annotate_frames
        self.calibration = calibration
        self._crossings = StopLineCrossings(calibration) if calibration else None
        self._turns = TrajectoryTurns(calibration) if calibration and calibration.exits else None
        self._signal_reader = SignalTimelineReader(signal_timeline) if signal_timeline else None

        self._tracker = VehicleTracker()
        self._quadrant_counter = QuadrantCounter()
        self._smoother = TemporalSmoother()
        self._annotator = FrameAnnotator()
        self._metrics = MetricsLogger(session_id)

        self._running = False
        self._frame_id = 0
        self._task: Optional[asyncio.Task] = None

        self._confidence_window: Deque[float] = deque(maxlen=10)
        self._CONFIDENCE_FALLBACK_THRESHOLD: float = 0.30   # < 30% avg conf triggers fallback
        self._confidence_fallback_active: bool = False
        self._last_good_weighted_counts: Optional[Dict[str, float]] = None
        self._fallback_frame_count: int = 0

        self._arrival_events: List[Dict[str, Any]] = []
        self._recorded_track_ids: Set[int] = set()

        self._aggregate_counts: Dict[str, int] = {
            "north_straight": 0, "north_left": 0, "north_right": 0,
            "south_straight": 0, "south_left": 0, "south_right": 0,
            "east_straight":  0, "east_left":  0, "east_right":  0,
            "west_straight":  0, "west_left":  0, "west_right":  0,
        }

    async def start(self) -> None:
        """Begin the pipeline loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        """Graceful shutdown."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        await self.video_processor.close()

    async def _loop(self) -> None:
        """Main pipeline loop running at PIPELINE_FPS."""
        target_interval = 1.0 / PIPELINE_FPS
        while self._running:
            tick_start = time.time()
            try:
                await self._tick()
            except Exception as e:
                print(f"[CCTVPipeline] Tick error: {e}")
            elapsed = time.time() - tick_start
            sleep_time = max(0.0, target_interval - elapsed)
            await asyncio.sleep(sleep_time)

    async def _tick(self) -> None:
        """Single pipeline iteration."""
        frame = await self.video_processor.read_frame()
        if frame is None:
            if self.video_processor.is_live:
            # Yield on transient buffer drop to allow stream decoder to recover.
                await asyncio.sleep(0.05)
                return
            eof_frame = CCTVFrame(
                frame_id=self._frame_id,
                timestamp_ms=time.time() * 1000,
                status="video_ended",
            )
            await self.on_frame(eof_frame)
            self._running = False
            return

        self._frame_id += 1
        source_time_s = getattr(self.video_processor, "source_time_s", None)
        tracking_time_s = time.monotonic() if self.video_processor.is_live else source_time_s
        recorded_signal = self._signal_reader.at(
            source_time_s,
            getattr(self.video_processor, "source_video_sha256", None),
        ) if self._signal_reader else None

        detection = await self.yolo_detector.detect(frame)
        detection.frame_id = self._frame_id
        detection.timestamp_ms = time.time() * 1000

        detection = self._tracker.update(detection, observation_time_s=tracking_time_s)
        fw = detection.frame_width or 1
        fh = detection.frame_height or 1
        time_s = round((self._frame_id - 1) / PIPELINE_FPS, 2)
        geometry = None
        if self.calibration is not None:
            directions, geometry = assign_approaches(detection, self.calibration)
        else:
            directions = [image_direction(b, fw, fh) for b in detection.bboxes]
        crossings = self._crossings.update(
            detection, directions, geometry, source_time_s
        ) if self._crossings else None
        turns = self._turns.update(detection, crossings) if self._turns else None

        for bbox, direction in zip(detection.bboxes, directions):
            if bbox.track_id is not None and bbox.track_id not in self._recorded_track_ids:
                if direction is None:
                    continue

                event = {
                    "type": "vehicle_arrival",
                    "vehicle_id": f"cctv_{bbox.track_id}",
                    "time_s": time_s,
                    "lane": direction,
                    "turn": None,
                    "event_semantics": "first_track_sighting_not_stop_line_arrival",
                    "direction_source": "configured_approach_region" if geometry else "image_direction_proxy",
                    "calibration_sha256": geometry.calibration_sha256 if geometry else None,
                    "turn_source": "unobserved",
                    "time_source": "processing_cadence_proxy",
                    "vehicle_type": bbox.class_name if bbox.class_name in ("car", "bus", "truck", "motorcycle", "auto_rickshaw") else "car",
                    "timestamp_ms": time.time() * 1000,
                }
                self._arrival_events.append(event)
                self._recorded_track_ids.add(bbox.track_id)

                if self.on_arrival is not None:
                    try:
                        await self.on_arrival(event)
                    except Exception as err:
                        print(f"[CCTVPipeline] on_arrival error: {err}")

        raw_counts_dict = self._quadrant_counter.count(detection) if geometry is None else {
            key: geometry.approach_counts.get(key.split("_")[0], 0) if key.endswith("_straight") else 0
            for key in self._aggregate_counts
        }
        raw_counts = LaneCounts(**raw_counts_dict)

        for k, v in raw_counts_dict.items():
            self._aggregate_counts[k] = self._aggregate_counts.get(k, 0) + v

        weighted_dict = {k: float(v) for k, v in raw_counts_dict.items()}
        weighted_counts = WeightedLaneCounts(**weighted_dict)

        if detection.bboxes:
            avg_conf = sum(b.confidence for b in detection.bboxes if b.confidence is not None) / max(len(detection.bboxes), 1)
        else:
            avg_conf = 0.0  # no detections → treat as low confidence
        self._confidence_window.append(avg_conf)

        rolling_conf = sum(self._confidence_window) / max(len(self._confidence_window), 1)

        if geometry is None and rolling_conf < self._CONFIDENCE_FALLBACK_THRESHOLD:
            if not self._confidence_fallback_active:
                logger.warning(
                    "[CCTVPipeline] Low confidence (%.2f < %.2f) — activating fallback to last-known-good counts.",
                    rolling_conf, self._CONFIDENCE_FALLBACK_THRESHOLD,
                )
                self._confidence_fallback_active = True
            self._fallback_frame_count += 1
            # Last-good display values are estimates; this pipeline issues no signal proposals.
            if self._last_good_weighted_counts is not None:
                weighted_dict = self._last_good_weighted_counts
                weighted_counts = WeightedLaneCounts.from_dict(weighted_dict)
        else:
            if self._confidence_fallback_active:
                logger.info(
                    "[CCTVPipeline] Confidence recovered (%.2f) — exiting fallback mode.",
                    rolling_conf,
                )
                self._confidence_fallback_active = False
            self._last_good_weighted_counts = dict(weighted_dict)

        smoothed_dict = self._smoother.update(weighted_dict)
        if geometry is not None:
            # Configured occupancy is current-frame evidence, never last-good imputation.
            smoothed_dict = {key: float(value) for key, value in raw_counts_dict.items()}
        smoothed_weighted = WeightedLaneCounts.from_dict(smoothed_dict)

        total_pressure = sum(smoothed_dict.values())
        pressure_ratio = total_pressure / (4 * 10.0)  # 4 main directions * max ~10 vehicles
        if pressure_ratio < 0.3:
            congestion = "LOW"
        elif pressure_ratio < 0.55:
            congestion = "MODERATE"
        elif pressure_ratio < 0.75:
            congestion = "HIGH"
        else:
            congestion = "CRITICAL"

        model_status = "model_not_loaded" if detection.model_not_loaded else "ok"

        annotated_b64 = None
        if self.annotate_frames:
            annotated = self._annotator.annotate_simple(frame, detection)
            if self.calibration is not None:
                annotated = draw_calibration(annotated, self.calibration)
            annotated_b64 = self._annotator.encode_frame_b64(
                annotated
            )

        self._metrics.log_frame(detection, raw_counts)

        if self.on_progress is not None:
            meta = self.video_processor.metadata
            total_frames = meta.total_frames if meta else None
            pct = (
                round((self._frame_id / total_frames) * 100)
                if total_frames and total_frames > 0
                else None
            )
            await self.on_progress({
                "type": "video_progress",
                "frame_id": self._frame_id,
                "total_frames": total_frames,
                "pct_complete": pct,
                "vehicles_detected_so_far": len(self._recorded_track_ids) if self._recorded_track_ids else sum(self._aggregate_counts.values()),
            })

        cctv_frame = CCTVFrame(
            frame_id=self._frame_id,
            timestamp_ms=time.time() * 1000,
            raw_counts=raw_counts,
            weighted_counts=smoothed_weighted,
            detection_fps=self._metrics.get_fps(),
            annotated_frame_b64=annotated_b64,
            vehicle_types=VehicleTypeBreakdown(**{
                name: sum(b.class_name == name for b in detection.bboxes)
                for name in VehicleTypeBreakdown.model_fields
            }),
            observation_contract=CameraObservationContract(
                count_semantics="configured_approach_region" if geometry else "exclusive_image_direction_proxy",
                detected_boxes=len(detection.bboxes), assigned_boxes=sum(raw_counts_dict.values()),
                unassigned_boxes=len(detection.bboxes)-sum(raw_counts_dict.values()),
            ),
            geometry_observation=geometry,
            crossing_observation=crossings,
            recorded_signal=recorded_signal,
            trajectory_observation=turns,
            trajectory_detection=detection if self._turns else None,
            congestion_level=congestion,
            status=model_status,
        )

        if self._confidence_fallback_active:
            cctv_frame.status = f"confidence_fallback_active | {model_status}"

        if recorded_signal and recorded_signal.status == "available":
            cctv_frame.observation_contract.missing_inputs[1] = "Complete signal timing and phase-service history"

        await self.on_frame(cctv_frame)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def arrival_events(self) -> List[Dict[str, Any]]:
        """Chronological vehicle arrivals detected across video frames."""
        return list(self._arrival_events)

    @property
    def aggregate_counts(self) -> Dict[str, int]:
        """Accumulated per-lane vehicle counts across all processed frames."""
        return dict(self._aggregate_counts)

    @property
    def session_metrics(self) -> Dict:
        return self._metrics.get_session_summary()

    @property
    def confidence_health(self) -> Dict[str, Any]:
        """Task 7.1: Returns detection confidence health metrics for monitoring."""
        rolling_conf = (
            sum(self._confidence_window) / max(len(self._confidence_window), 1)
            if self._confidence_window else 0.0
        )
        return {
            "rolling_avg_confidence":    round(rolling_conf, 3),
            "fallback_active":           self._confidence_fallback_active,
            "fallback_frames_triggered": self._fallback_frame_count,
            "fallback_threshold":        self._CONFIDENCE_FALLBACK_THRESHOLD,
        }
