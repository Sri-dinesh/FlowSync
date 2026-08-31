"""
CCTV WebSocket Handler — /ws/cctv
Redesigned: No ROI required. Uses QuadrantCounter for full-frame detection.
Broadcasts progress events during video processing.
"""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Dict, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect

from ..realworld.models.config import SESSION_DIR, UPLOAD_DIR
from ..realworld.models.schemas import CCTVFrame
from ..realworld.pipeline.cctv_pipeline import CCTVPipeline
from ..realworld.pipeline.video_processor import VideoProcessor
from ..realworld.pipeline.yolo_detector import YOLODetector
from ..realworld.digital_twin.session_recorder import SessionRecorder


class CCTVConnectionManager:
    """Manages WebSocket connections for /ws/cctv."""

    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)

    async def broadcast(self, data: dict) -> None:
        dead = set()
        for ws in self._connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._connections.discard(ws)

    async def send(self, ws: WebSocket, data: dict) -> None:
        try:
            await ws.send_json(data)
        except Exception:
            self._connections.discard(ws)


# Module-level connection manager
cctv_manager = CCTVConnectionManager()

# Per-connection pipeline + recorder state
_pipelines: Dict[str, CCTVPipeline] = {}
_recorders: Dict[str, SessionRecorder] = {}


async def cctv_socket(websocket: WebSocket) -> None:
    """WebSocket endpoint for /ws/cctv."""
    await cctv_manager.connect(websocket)
    conn_id = str(uuid.uuid4())
    pipeline: Optional[CCTVPipeline] = None
    recorder: Optional[SessionRecorder] = None

    async def on_frame(frame: CCTVFrame) -> None:
        """Callback: pipeline emits a frame → broadcast to client."""
        if recorder:
            recorder.record_frame(frame)

        data = frame.model_dump(mode="json")
        data["type"] = "cctv_frame"

        # When the video finishes, attach twin_data to the status message
        if frame.status == "video_ended" and recorder:
            if pipeline:
                recorder.set_arrivals(pipeline.arrival_events)
            recorder.save()
            twin_data = recorder.get_twin_data()
            await cctv_manager.send(websocket, {
                "type": "pipeline_status",
                "status": "completed",
                "session_id": recorder.session_id,
                "stats": recorder.get_stats(),
                "twin_data": twin_data,
            })
        else:
            await cctv_manager.send(websocket, data)

    async def on_progress(progress: dict) -> None:
        """Callback: pipeline emits progress → forward to client."""
        await cctv_manager.send(websocket, progress)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await cctv_manager.send(websocket, {
                    "type": "error", "code": "INVALID_JSON", "message": "Bad JSON"
                })
                continue

            cmd = msg.get("command", "")
            payload = msg.get("payload", {})

            if cmd == "start_processing":
                video_path = payload.get("video_path", "")

                if not os.path.exists(video_path):
                    await cctv_manager.send(websocket, {
                        "type": "error",
                        "code": "VIDEO_NOT_FOUND",
                        "message": f"Video not found: {video_path}",
                    })
                    continue

                # Stop any running pipeline first
                if pipeline:
                    await pipeline.stop()

                # Get YOLO detector from app state
                yolo_detector: YOLODetector = getattr(websocket.app.state, 'yolo_detector', None)
                if yolo_detector is None:
                    yolo_detector = YOLODetector()
                    try:
                        await yolo_detector.load_model()
                        print(f"[cctv_ws] YOLO detector loaded on demand: {yolo_detector.device}")
                    except Exception as e:
                        print(f"[cctv_ws] YOLO detector not available: {e}")

                session_id = f"session_{conn_id[:8]}"
                recorder = SessionRecorder(session_id, SESSION_DIR)

                video_proc = VideoProcessor(video_path)
                await video_proc.open()

                pipeline = CCTVPipeline(
                    video_processor=video_proc,
                    yolo_detector=yolo_detector,
                    on_frame=on_frame,
                    on_progress=on_progress,
                    session_id=session_id,
                )
                _pipelines[conn_id] = pipeline
                _recorders[conn_id] = recorder

                await pipeline.start()
                await cctv_manager.send(websocket, {
                    "type": "pipeline_status",
                    "status": "started",
                    "session_id": session_id,
                })

            elif cmd == "stop_processing":
                if pipeline and recorder:
                    recorder.set_arrivals(pipeline.arrival_events)
                if pipeline:
                    await pipeline.stop()
                    pipeline = None
                if recorder:
                    path = recorder.save()
                    twin_data = recorder.get_twin_data()
                    await cctv_manager.send(websocket, {
                        "type": "pipeline_status",
                        "status": "stopped",
                        "session_id": recorder.session_id,
                        "session_saved": path,
                        "stats": recorder.get_stats(),
                        "twin_data": twin_data,
                    })
                    recorder = None

            elif cmd == "set_confidence_threshold":
                # Future: dynamically update YOLO confidence threshold
                pass

            else:
                await cctv_manager.send(websocket, {
                    "type": "error", "code": "UNKNOWN_COMMAND",
                    "message": f"Unknown command: {cmd}",
                })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[cctv_ws] Error: {e}")
    finally:
        cctv_manager.disconnect(websocket)
        if pipeline:
            await pipeline.stop()
        if recorder:
            recorder.save()
        _pipelines.pop(conn_id, None)
        _recorders.pop(conn_id, None)
