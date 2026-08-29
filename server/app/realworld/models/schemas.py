"""
FlowSync Real-World CCTV Integration — Pydantic Schemas
All data models for the CCTV pipeline, detection outputs, ROI configs, and training.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from .config import LANE_KEYS


# ══════════════════════════════════════════════════════════════════════════════
# Detection Schemas
# ══════════════════════════════════════════════════════════════════════════════

class BoundingBox(BaseModel):
    model_config = ConfigDict(frozen=False)

    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float          # 0.0 - 1.0
    class_id: int              # 0-6 (unified class IDs)
    class_name: str            # "car", "auto_rickshaw", etc.
    track_id: Optional[int] = None    # ByteTrack ID (None if tracking disabled)

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def bottom_center(self) -> Tuple[float, float]:
        """Vehicle's ground contact point — best for lane assignment."""
        return ((self.x1 + self.x2) / 2, self.y2)

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1


class VehicleDetection(BaseModel):
    model_config = ConfigDict(frozen=False)

    frame_id: int
    timestamp_ms: float
    bboxes: List[BoundingBox] = Field(default_factory=list)
    inference_time_ms: float = 0.0
    frame_width: int = 640
    frame_height: int = 640
    model_not_loaded: bool = False  # True when model hasn't been trained yet


# ══════════════════════════════════════════════════════════════════════════════
# Lane Count Schemas
# ══════════════════════════════════════════════════════════════════════════════

class LaneCounts(BaseModel):
    """Raw vehicle counts for all 12 movement lanes."""
    model_config = ConfigDict(frozen=False)

    north_straight: int = 0
    north_left: int = 0
    north_right: int = 0
    south_straight: int = 0
    south_left: int = 0
    south_right: int = 0
    east_straight: int = 0
    east_left: int = 0
    east_right: int = 0
    west_straight: int = 0
    west_left: int = 0
    west_right: int = 0

    def to_dict(self) -> Dict[str, int]:
        return self.model_dump()

    def total(self) -> int:
        return sum(self.to_dict().values())

    @classmethod
    def from_dict(cls, d: Dict[str, int]) -> "LaneCounts":
        return cls(**{k: d.get(k, 0) for k in LANE_KEYS})


class WeightedLaneCounts(BaseModel):
    """Vehicle-type-weighted queue values per lane (float, not int)."""
    model_config = ConfigDict(frozen=False)

    north_straight: float = 0.0
    north_left: float = 0.0
    north_right: float = 0.0
    south_straight: float = 0.0
    south_left: float = 0.0
    south_right: float = 0.0
    east_straight: float = 0.0
    east_left: float = 0.0
    east_right: float = 0.0
    west_straight: float = 0.0
    west_left: float = 0.0
    west_right: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return self.model_dump()

    def total(self) -> float:
        return sum(self.to_dict().values())

    @classmethod
    def from_dict(cls, d: Dict[str, float]) -> "WeightedLaneCounts":
        return cls(**{k: d.get(k, 0.0) for k in LANE_KEYS})


class VehicleTypeBreakdown(BaseModel):
    model_config = ConfigDict(frozen=False)

    bicycle: int = 0
    motorcycle: int = 0
    car: int = 0
    auto_rickshaw: int = 0
    van: int = 0
    bus: int = 0
    truck: int = 0

    def total(self) -> int:
        return self.bicycle + self.motorcycle + self.car + self.auto_rickshaw + self.van + self.bus + self.truck


# ══════════════════════════════════════════════════════════════════════════════
# ROI Schemas
# ══════════════════════════════════════════════════════════════════════════════

class ROIPolygon(BaseModel):
    model_config = ConfigDict(frozen=False)

    lane_id: str              # e.g. "north_straight"
    vertices: List[Tuple[float, float]]  # [(x,y)...] in relative [0-1] coords
    color: Optional[str] = None  # hex color for display


class ROIConfig(BaseModel):
    model_config = ConfigDict(frozen=False)

    intersection_id: str
    camera_id: str
    frame_width: int
    frame_height: int
    rois: List[ROIPolygon] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def get_roi(self, lane_id: str) -> Optional[ROIPolygon]:
        for roi in self.rois:
            if roi.lane_id == lane_id:
                return roi
        return None

    def to_pixel_coords(self, polygon: ROIPolygon) -> List[Tuple[float, float]]:
        """Convert relative [0-1] polygon coords to pixel coords."""
        return [
            (x * self.frame_width, y * self.frame_height)
            for x, y in polygon.vertices
        ]


# ══════════════════════════════════════════════════════════════════════════════
# Pipeline Output Schema
# ══════════════════════════════════════════════════════════════════════════════

class CCTVFrame(BaseModel):
    """Complete output from one pipeline cycle."""
    model_config = ConfigDict(frozen=False)

    frame_id: int
    timestamp_ms: float
    # Detection outputs
    raw_counts: LaneCounts = Field(default_factory=LaneCounts)
    weighted_counts: WeightedLaneCounts = Field(default_factory=WeightedLaneCounts)
    vehicle_types: VehicleTypeBreakdown = Field(default_factory=VehicleTypeBreakdown)
    detection_fps: float = 0.0
    # RL outputs
    observation: List[float] = Field(default_factory=lambda: [0.0] * 20)
    signal_phase: int = 0
    signal_phase_name: str = "NS_STRAIGHT"
    q_values: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    confidence_pct: float = 0.0
    # Frame (base64 for WebSocket streaming)
    annotated_frame_b64: Optional[str] = None
    # Fixed timer comparison
    fixed_timer_phase: Optional[int] = None
    fixed_timer_phase_name: Optional[str] = None
    # Metrics
    estimated_avg_wait: float = 0.0
    congestion_level: str = "LOW"
    # Status
    status: str = "ok"  # "ok" | "video_ended" | "roi_required" | "model_loading"


# ══════════════════════════════════════════════════════════════════════════════
# Training Schemas
# ══════════════════════════════════════════════════════════════════════════════

class TrainingConfig(BaseModel):
    model_config = ConfigDict(frozen=False)

    model_size: str = "yolov8n"       # n, s, m, l, x
    epochs: int = 100
    batch_size: int = 16
    image_size: int = 640
    learning_rate: float = 0.01
    patience: int = 15                # Early stopping patience
    augment: bool = True
    amp: bool = True                  # Mixed precision
    device: str = "auto"              # "cpu", "cuda", "mps", "auto"
    pretrained_weights: str = "yolov8n.pt"


class ValidationMetrics(BaseModel):
    model_config = ConfigDict(frozen=False)

    map50: float = 0.0                # mAP @ IoU 0.50
    map50_95: float = 0.0             # mAP @ IoU 0.50:0.95
    precision: float = 0.0
    recall: float = 0.0
    per_class_ap: Dict[str, float] = Field(default_factory=dict)
    inference_fps_cpu: float = 0.0
    inference_fps_gpu: Optional[float] = None
    model_size_mb: float = 0.0


class TrainingResult(BaseModel):
    model_config = ConfigDict(frozen=False)

    best_map50: float = 0.0
    best_map50_95: float = 0.0
    total_epochs: int = 0
    best_epoch: int = 0
    model_path: str = ""
    training_time_seconds: float = 0.0


# ══════════════════════════════════════════════════════════════════════════════
# Digital Twin Schemas
# ══════════════════════════════════════════════════════════════════════════════

class TrafficFlowParams(BaseModel):
    """Calibrated flow parameters extracted from detection sessions."""
    model_config = ConfigDict(frozen=False)

    intersection_id: str = "default"
    time_period: str = "off_peak"      # "morning_peak", "evening_peak", "off_peak"
    spawn_rates: Dict[str, float] = Field(default_factory=dict)   # {"north_straight": 0.8, ...}
    turn_ratios: Dict[str, Dict[str, float]] = Field(default_factory=dict)  # {"north": {"straight": 0.5, ...}}
    vehicle_type_distribution: Dict[str, float] = Field(
        default_factory=lambda: {
            "bicycle": 0.05, "motorcycle": 0.40, "car": 0.35,
            "auto_rickshaw": 0.10, "van": 0.05, "bus": 0.03, "truck": 0.02
        }
    )
    peak_hours: List[int] = Field(default_factory=lambda: [8, 9, 17, 18])
    avg_vehicles_per_minute: float = 0.0


class DatasetStats(BaseModel):
    model_config = ConfigDict(frozen=False)

    total_images: int = 0
    train_count: int = 0
    val_count: int = 0
    test_count: int = 0
    per_class_counts: Dict[str, int] = Field(default_factory=dict)
    sources: Dict[str, int] = Field(default_factory=dict)
    has_auto_rickshaw: bool = False


class VideoMetadata(BaseModel):
    model_config = ConfigDict(frozen=False)

    width: int
    height: int
    source_fps: float
    target_fps: float
    total_frames: Optional[int] = None
    duration_seconds: Optional[float] = None
    source_type: str = "file"  # "file" | "rtsp" | "http"


class TrackState(BaseModel):
    model_config = ConfigDict(frozen=False)

    track_id: int
    class_name: str
    lane_id: Optional[str] = None
    first_seen_ms: float = 0.0
    last_seen_ms: float = 0.0
    is_moving: bool = True
    wait_time_seconds: float = 0.0
    centroid_history: List[Tuple[float, float]] = Field(default_factory=list)
