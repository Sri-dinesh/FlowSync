"""
CCTV REST API Router — /cctv endpoints for video upload, sessions, model status, and digital twin data.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..realworld.models.config import (
    SESSION_DIR,
    UPLOAD_DIR,
    MAX_UPLOAD_SIZE_MB,
    YOLO_PRODUCTION_PATH,
)

router = APIRouter(prefix="/cctv", tags=["cctv"])

# ── Video Management ──────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_video(file: UploadFile) -> Dict[str, str]:
    """Upload a video file. Returns video_path and video_id."""
    upload_dir = Path(UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(413, f"File too large (max {MAX_UPLOAD_SIZE_MB}MB)")

    video_id = str(uuid.uuid4())[:8]
    safe_name = Path(file.filename).name if file.filename else "upload.mp4"
    out_path = upload_dir / f"{video_id}_{safe_name}"

    with open(out_path, "wb") as f:
        f.write(content)

    return {"video_id": video_id, "video_path": str(out_path), "filename": safe_name}


@router.get("/videos")
async def list_videos() -> List[Dict[str, Any]]:
    """List all uploaded videos."""
    upload_dir = Path(UPLOAD_DIR)
    if not upload_dir.exists():
        return []
    videos = []
    for f in upload_dir.iterdir():
        if f.is_file() and f.suffix in (".mp4", ".avi", ".mov", ".mkv"):
            videos.append({
                "filename": f.name,
                "path": str(f),
                "size_mb": round(f.stat().st_size / (1024 * 1024), 2),
            })
    return videos


@router.delete("/videos/{filename}")
async def delete_video(filename: str) -> Dict[str, str]:
    """Delete an uploaded video file."""
    path = Path(UPLOAD_DIR) / filename
    if not path.exists():
        raise HTTPException(404, f"Video not found: {filename}")
    path.unlink()
    return {"deleted": filename}


# ── Session Management ────────────────────────────────────────────────────────

@router.get("/sessions")
async def list_sessions() -> List[Dict[str, Any]]:
    """List all saved detection sessions."""
    sessions_dir = Path(SESSION_DIR)
    if not sessions_dir.exists():
        return []
    sessions = []
    for f in sessions_dir.glob("*.json"):
        import json
        try:
            with open(f) as fp:
                data = json.load(fp)
            sessions.append({
                "session_id": data.get("session_id", f.stem),
                "filename": f.name,
                "stats": data.get("stats", {}),
            })
        except Exception:
            pass
    return sessions


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> Dict[str, Any]:
    """Get full stats for a specific session."""
    import json
    path = Path(SESSION_DIR) / f"{session_id}.json"
    if not path.exists():
        raise HTTPException(404, f"Session not found: {session_id}")
    with open(path) as f:
        data = json.load(f)
    return data.get("stats", {})


@router.get("/sessions/{session_id}/twin-data")
async def get_session_twin_data(session_id: str) -> Dict[str, Any]:
    """
    Get Digital Twin seeding data for a specific session.
    Returns aggregate vehicle counts per lane for spawning vehicles in the 3D twin.
    """
    import json
    path = Path(SESSION_DIR) / f"{session_id}.json"
    if not path.exists():
        raise HTTPException(404, f"Session not found: {session_id}")
    with open(path) as f:
        data = json.load(f)

    # Return twin_data if present (new format), otherwise build from stats
    if "twin_data" in data:
        return data["twin_data"]

    # Legacy fallback: return aggregate from stats
    stats = data.get("stats", {})
    return {
        "session_id": session_id,
        "total_frames_processed": stats.get("frame_count", 0),
        "total_vehicles_detected": stats.get("total_detections", 0),
        "aggregate_counts": stats.get("aggregate_counts", {}),
        "peak_counts": {},
        "avg_counts": {},
    }


# ── Model Status ──────────────────────────────────────────────────────────────

@router.get("/model/status")
async def model_status(request: Request) -> Dict[str, Any]:
    """YOLO model load status, version, and metrics."""
    try:
        detector = request.app.state.yolo_detector
        return {
            "is_loaded": detector.is_loaded,
            "model_path": detector.model_path,
            "device": detector.device,
            "is_custom_model": detector.is_custom_model,
            "production_exists": os.path.exists(YOLO_PRODUCTION_PATH),
        }
    except AttributeError:
        return {
            "is_loaded": False,
            "model_path": None,
            "device": "cpu",
            "is_custom_model": False,
            "production_exists": os.path.exists(YOLO_PRODUCTION_PATH),
        }


class LoadModelRequest(BaseModel):
    model_path: str


@router.post("/model/load")
async def load_model(request: Request, body: LoadModelRequest) -> Dict[str, Any]:
    """Load a YOLO model from the specified path."""
    if not os.path.exists(body.model_path):
        raise HTTPException(404, f"Model not found: {body.model_path}")
    try:
        detector = request.app.state.yolo_detector
        await detector.load_model(body.model_path)
        return {"loaded": True, "model_path": body.model_path, "device": detector.device}
    except Exception as e:
        raise HTTPException(500, f"Failed to load model: {e}")
