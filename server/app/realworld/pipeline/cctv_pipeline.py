"""
CCTVPipeline — Main orchestrator. Ties all pipeline steps into a single async loop.
Runs at PIPELINE_FPS (2Hz), handling video frames, YOLO detection, quadrant-based
vehicle counting, temporal smoothing, annotation, and WebSocket broadcast.

ROI polygons are NOT required. The QuadrantCounter assigns vehicles to directions
based on where their bounding-box bottom-center falls within the frame.
"""
from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable, Dict, Optional

from ..models.config import (
    MAX_GREEN_TIME,
    PHASE_NAMES,
    PIPELINE_FPS,
)
from ..models.schemas import (
    CCTVFrame,
    LaneCounts,
    VehicleDetection,
    WeightedLaneCounts,
)
from .frame_annotator import FrameAnnotator
from .quadrant_counter import QuadrantCounter
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
    3. Count vehicles per direction (QuadrantCounter) — no ROI needed
    4. Apply temporal smoothing (TemporalSmoother)
    5. Annotate frame with bboxes (FrameAnnotator) — base64 encode
    6. Emit CCTVFrame via callback (for WebSocket broadcast)
    7. Log metrics (MetricsLogger)
    """

    def __init__(
        self,
        video_processor: VideoProcessor,
        yolo_detector: YOLODetector,
        on_frame: Callable[[CCTVFrame], Awaitable[None]],
        on_progress: Optional[Callable[[Dict], Awaitable[None]]] = None,
        session_id: str = "session_001",
        annotate_frames: bool = True,
    ) -> None:
        self.video_processor = video_processor
        self.yolo_detector = yolo_detector
        self.on_frame = on_frame
        self.on_progress = on_progress
        self.session_id = session_id
        self.annotate_frames = annotate_frames

        self._quadrant_counter = QuadrantCounter()
        self._smoother = TemporalSmoother()
        self._annotator = FrameAnnotator()
        self._metrics = MetricsLogger(session_id)

        self._running = False
        self._frame_id = 0
        self._task: Optional[asyncio.Task] = None

        # Aggregate counts accumulated across all frames
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
        # 1. Extract frame
        frame = await self.video_processor.read_frame()
        if frame is None:
            # End of video — emit completion frame
            eof_frame = CCTVFrame(
                frame_id=self._frame_id,
                timestamp_ms=time.time() * 1000,
                status="video_ended",
            )
            await self.on_frame(eof_frame)
            self._running = False
            return

        self._frame_id += 1

        # 2. YOLO detection (returns empty bboxes if model not loaded)
        detection = await self.yolo_detector.detect(frame)
        detection.frame_id = self._frame_id
        detection.timestamp_ms = time.time() * 1000

        # 3. Count vehicles per lane using quadrant heuristic
        raw_counts_dict = self._quadrant_counter.count(detection)
        raw_counts = LaneCounts(**raw_counts_dict)

        # Accumulate into aggregate
        for k, v in raw_counts_dict.items():
            self._aggregate_counts[k] = self._aggregate_counts.get(k, 0) + v

        # Build WeightedLaneCounts (1:1 weight for quadrant counting)
        weighted_dict = {k: float(v) for k, v in raw_counts_dict.items()}
        weighted_counts = WeightedLaneCounts(**weighted_dict)

        # 4. Temporal smoothing
        smoothed_dict = self._smoother.update(weighted_dict)
        smoothed_weighted = WeightedLaneCounts.from_dict(smoothed_dict)

        # 5. Congestion metrics
        total_pressure = sum(smoothed_dict.values())
        estimated_wait = min(120.0, total_pressure * 2.5)
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

        # 6. Annotate frame
        annotated_b64 = None
        if self.annotate_frames:
            annotated_b64 = self._annotator.encode_frame_b64(
                self._annotator.annotate_simple(frame, detection)
            )

        # 7. Log metrics
        self._metrics.log_frame(detection, raw_counts)

        # 8. Emit progress to WebSocket (every frame)
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
                "vehicles_detected_so_far": sum(self._aggregate_counts.values()),
            })

        # 9. Build and emit complete CCTVFrame
        cctv_frame = CCTVFrame(
            frame_id=self._frame_id,
            timestamp_ms=time.time() * 1000,
            raw_counts=raw_counts,
            weighted_counts=smoothed_weighted,
            detection_fps=self._metrics.get_fps(),
            annotated_frame_b64=annotated_b64,
            estimated_avg_wait=estimated_wait,
            congestion_level=congestion,
            status=model_status,
        )

        await self.on_frame(cctv_frame)

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def aggregate_counts(self) -> Dict[str, int]:
        """Accumulated per-lane vehicle counts across all processed frames."""
        return dict(self._aggregate_counts)

    @property
    def session_metrics(self) -> Dict:
        return self._metrics.get_session_summary()
