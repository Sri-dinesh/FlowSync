"""
Frame extraction from video files or RTSP streams.
Provides frames at configurable FPS, independent of source FPS.
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Optional, Union

import numpy as np

from ..models.config import PIPELINE_FPS
from ..models.schemas import VideoMetadata


class VideoProcessor:
    """
    Extracts frames from:
    - Local video file (.mp4, .avi, .mov, .mkv)
    - RTSP URL (live CCTV stream)
    - MJPEG HTTP stream

    Provides frames at configurable FPS, independent of source FPS.
    Example: 25fps source -> 2fps output (extracts every 12th frame)
    """

    def __init__(
        self,
        source: Union[str, Path],
        target_fps: float = PIPELINE_FPS,
    ) -> None:
        self.source = str(source)
        self.target_fps = target_fps
        self._cap = None
        self._frame_counter = 0
        self._source_fps = 25.0
        self._frame_interval = 1
        self._metadata: Optional[VideoMetadata] = None
        self._last_frame_time: float = 0.0

    async def open(self) -> VideoMetadata:
        """Open video source and return metadata."""
        try:
            import cv2
        except ImportError:
            raise RuntimeError("OpenCV not installed. Run: pip install opencv-python-headless")

        def _open_capture():
            if self.source.startswith("rtsp://") or self.source.startswith("http://"):
                cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
                # Minimize buffer for live streams
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                source_type = "rtsp" if self.source.startswith("rtsp://") else "http"
            else:
                cap = cv2.VideoCapture(self.source)
                source_type = "file"
            return cap, source_type

        cap, source_type = await asyncio.to_thread(_open_capture)

        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video source: {self.source}")

        self._cap = cap
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        source_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames_raw = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        total_frames = total_frames_raw if total_frames_raw > 0 and source_type == "file" else None
        duration = (total_frames / source_fps) if total_frames else None

        self._source_fps = source_fps
        self._frame_interval = max(1, int(source_fps / self.target_fps))

        self._metadata = VideoMetadata(
            width=width,
            height=height,
            source_fps=source_fps,
            target_fps=self.target_fps,
            total_frames=total_frames,
            duration_seconds=duration,
            source_type=source_type,
        )
        return self._metadata

    async def read_frame(self) -> Optional[np.ndarray]:
        """
        Read next frame at target_fps.
        Returns BGR numpy array, or None if end of stream.
        """
        if self._cap is None:
            raise RuntimeError("VideoProcessor not opened. Call open() first.")

        def _read():
            # Skip frames to match target FPS
            frame = None
            for _ in range(self._frame_interval):
                ret, f = self._cap.read()
                if not ret:
                    return None
                frame = f
            self._frame_counter += self._frame_interval
            return frame

        # For live streams: throttle read rate to avoid busy-loop
        if self.is_live:
            elapsed = time.time() - self._last_frame_time
            target_interval = 1.0 / self.target_fps
            if elapsed < target_interval:
                await asyncio.sleep(target_interval - elapsed)

        frame = await asyncio.to_thread(_read)
        self._last_frame_time = time.time()
        return frame

    def get_frame_at(self, frame_id: int) -> Optional[np.ndarray]:
        """Seek to specific frame (file mode only)."""
        if self._cap is None or self.is_live:
            return None
        try:
            import cv2
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
            ret, frame = self._cap.read()
            return frame if ret else None
        except Exception:
            return None

    async def close(self) -> None:
        """Release video capture resources."""
        if self._cap is not None:
            await asyncio.to_thread(self._cap.release)
            self._cap = None

    @property
    def is_live(self) -> bool:
        """True for RTSP/HTTP streams, False for file sources."""
        return self.source.startswith("rtsp://") or self.source.startswith("http://")

    @property
    def frame_interval(self) -> int:
        """Source frames to skip between extractions."""
        return self._frame_interval

    @property
    def current_frame_id(self) -> int:
        return self._frame_counter

    @property
    def metadata(self) -> Optional[VideoMetadata]:
        return self._metadata
