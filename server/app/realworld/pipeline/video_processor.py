"""
Frame extraction from video files, RTSP streams, or live YouTube broadcasts.
Provides frames at configurable FPS, with zero-lag real-time grabber for live streams.
"""
from __future__ import annotations

import asyncio
import os
import threading
import time
from pathlib import Path
from typing import Optional, Union

import numpy as np

from ..models.config import PIPELINE_FPS
from ..models.schemas import VideoMetadata
from .stream_resolver import StreamResolver


class RealtimeFrameGrabber:
    """
    Dedicated daemon background thread for live streams (RTSP, HLS, YouTube).
    Continuously calls cap.grab() to drain hardware/network buffers at native stream rate.
    Maintains an atomic single-frame slot (self._latest_frame) so downstream AI inference
    always retrieves the absolute newest real-time frame with 0.0ms queue lag.
    """

    def __init__(self, cap) -> None:
        self._cap = cap
        self._running = True
        self._lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while self._running:
            if not self._cap or not self._cap.isOpened():
                break
            try:
                grabbed = self._cap.grab()
                if not grabbed:
                    time.sleep(0.005)
                    continue
                ret, frame = self._cap.retrieve()
                if ret and frame is not None:
                    with self._lock:
                        self._latest_frame = frame
            except Exception:
                time.sleep(0.01)

    def read_latest(self) -> Optional[np.ndarray]:
        with self._lock:
            return self._latest_frame

    def stop(self) -> None:
        self._running = False
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)


class VideoProcessor:
    """
    Extracts frames from:
    - Local video file (.mp4, .avi, .mov, .mkv)
    - YouTube live stream URL (resolves via StreamResolver)
    - RTSP URL (live CCTV stream)
    - MJPEG / HLS HTTP stream

    Provides frames at configurable FPS, independent of source FPS.
    For live streams: uses RealtimeFrameGrabber to ensure 0ms buffer delay.
    """

    def __init__(
        self,
        source: Union[str, Path],
        target_fps: float = PIPELINE_FPS,
    ) -> None:
        self.source = str(source).strip()
        self.target_fps = target_fps
        self._resolved_url: str = self.source
        self._cap = None
        self._grabber: Optional[RealtimeFrameGrabber] = None
        self._frame_counter = 0
        self._source_fps = 25.0
        self._frame_interval = 1
        self._metadata: Optional[VideoMetadata] = None
        self._last_frame_time: float = 0.0

    async def open(self) -> VideoMetadata:
        """Open video source (resolving stream URLs if necessary) and return metadata."""
        try:
            import cv2
        except ImportError:
            raise RuntimeError("OpenCV not installed. Run: pip install opencv-python-headless")

        # Configure OpenCV FFmpeg environment to avoid stream connection timeout & send standard browser user-agent
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
            "user_agent;Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36|"
            "timeout;15000000|"
            "reconnect;1|"
            "reconnect_streamed;1|"
            "reconnect_delay_max;2"
        )

        # Resolve stream URL if network source (e.g. YouTube live -> direct HLS .m3u8)
        if self.is_live:
            self._resolved_url = await StreamResolver.resolve(self.source)

        def _open_capture(url: str):
            if self.is_live:
                cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
                # Minimize internal buffer to 1 frame for ultra-low latency
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                if hasattr(cv2, "CAP_PROP_OPEN_TIMEOUT_MSEC"):
                    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 15000)
                if hasattr(cv2, "CAP_PROP_READ_TIMEOUT_MSEC"):
                    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 15000)

                if StreamResolver.is_youtube_url(self.source):
                    source_type = "youtube"
                elif self.source.startswith("rtsp://"):
                    source_type = "rtsp"
                else:
                    source_type = "http"
            else:
                cap = cv2.VideoCapture(url)
                source_type = "file"
            return cap, source_type

        cap, source_type = await asyncio.to_thread(_open_capture, self._resolved_url)

        # If opening failed on a live stream, retry once with fresh resolution
        if not cap.isOpened() and self.is_live:
            print(f"[VideoProcessor] Initial open failed for {self._resolved_url[:60]}..., retrying resolution...")
            self._resolved_url = await StreamResolver.resolve(self.source)
            cap, source_type = await asyncio.to_thread(_open_capture, self._resolved_url)

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

        # Start low-latency zero-buffer background grabber for live streams
        if self.is_live:
            self._grabber = RealtimeFrameGrabber(self._cap)
            for _ in range(40):
                if self._grabber.read_latest() is not None:
                    break
                await asyncio.sleep(0.05)

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
        For live streams: retrieves the latest real-time frame with 0ms queue delay.
        For file playback: steps through frames sequentially.
        Returns BGR numpy array, or None if end of stream.
        """
        if self._cap is None:
            raise RuntimeError("VideoProcessor not opened. Call open() first.")

        if self.is_live:
            # Enforce target FPS pacing for live ingestion
            elapsed = time.time() - self._last_frame_time
            target_interval = 1.0 / self.target_fps
            if elapsed < target_interval:
                await asyncio.sleep(target_interval - elapsed)

            frame = self._grabber.read_latest() if self._grabber else None
            self._frame_counter += 1
            self._last_frame_time = time.time()
            return frame

        def _read_file():
            # Skip frames to match target FPS
            frame = None
            for _ in range(self._frame_interval):
                ret, f = self._cap.read()
                if not ret:
                    return None
                frame = f
            self._frame_counter += self._frame_interval
            return frame

        frame = await asyncio.to_thread(_read_file)
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
        """Release video capture resources and background grabber thread."""
        if self._grabber is not None:
            self._grabber.stop()
            self._grabber = None

        if self._cap is not None:
            await asyncio.to_thread(self._cap.release)
            self._cap = None

    @property
    def is_live(self) -> bool:
        """True for YouTube live, RTSP, HLS, or HTTP streams; False for local files."""
        return StreamResolver.is_stream_url(self.source)

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
