"""
FlowSync Real-World CCTV Integration — Configuration
Single source of truth for all constants. No hardcoding anywhere else.
"""
from typing import Dict, List

# ── Model Config ──────────────────────────────────────────────────────────────
YOLO_MODEL_SIZE: str = "yolov8n"
YOLO_PRETRAINED_PATH: str = "models/yolo/pretrained/yolov8n.pt"
YOLO_PRODUCTION_PATH: str = "models/yolo/production/best.pt"
YOLO_ONNX_PATH: str = "models/yolo/production/best.onnx"
USE_ONNX: bool = True  # Enabled ONNX production inference
YOLO_CONF_THRESHOLD: float = 0.35
YOLO_NMS_IOU: float = 0.45
YOLO_IMGSZ: int = 640

# ── Vehicle Classes ────────────────────────────────────────────────────────────
VEHICLE_CLASSES: Dict[int, str] = {
    0: "bicycle",
    1: "motorcycle",
    2: "car",
    3: "auto_rickshaw",
    4: "van",
    5: "bus",
    6: "truck",
}

# COCO pretrained class ID → unified class name (for before fine-tuning)
COCO_TO_UNIFIED: Dict[int, str] = {
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}

VEHICLE_QUEUE_WEIGHTS: Dict[str, float] = {
    "bicycle": 0.3,
    "motorcycle": 0.5,
    "car": 1.0,
    "auto_rickshaw": 1.3,
    "van": 1.5,
    "bus": 3.0,
    "truck": 2.5,
}

# ── Pipeline Config ────────────────────────────────────────────────────────────
PIPELINE_FPS: float = 2.0               # 2 frames/sec — sufficient for signal control
FRAME_BUFFER_SIZE: int = 30             # Ring buffer depth
TEMPORAL_SMOOTHING_ALPHA: float = 0.3   # EMA alpha for queue count smoothing

# ── Lane Convention ────────────────────────────────────────────────────────────
LANE_KEYS: List[str] = [
    "north_straight", "north_left", "north_right",
    "south_straight", "south_left", "south_right",
    "east_straight", "east_left", "east_right",
    "west_straight", "west_left", "west_right",
]

# Direction groups
DIRECTION_GROUPS: Dict[str, List[str]] = {
    "north": ["north_straight", "north_left", "north_right"],
    "south": ["south_straight", "south_left", "south_right"],
    "east": ["east_straight", "east_left", "east_right"],
    "west": ["west_straight", "west_left", "west_right"],
}

# ROI annotation colors per direction (BGR for OpenCV)
DIRECTION_COLORS_BGR: Dict[str, tuple] = {
    "north": (0, 255, 0),    # green
    "south": (0, 0, 255),    # red
    "east": (255, 0, 0),     # blue
    "west": (0, 255, 255),   # yellow
}

# ── Observation Space ──────────────────────────────────────────────────────────
MAX_QUEUE_CAP: float = 10.0             # Same as simulation (normalization denominator)
MAX_GREEN_TIME: float = 40.0            # Same as simulation
STARVATION_THRESHOLD: float = 45.0     # Same as simulation
OBS_DIM: int = 20                       # Observation vector dimension

# ── Signal Phases ──────────────────────────────────────────────────────────────
PHASE_NAMES: Dict[int, str] = {
    0: "NS_STRAIGHT",
    1: "EW_STRAIGHT",
    2: "NS_LEFT",
    3: "EW_LEFT",
}

# ── Paths ──────────────────────────────────────────────────────────────────────
ROI_CONFIG_DIR: str = "data/roi_configs"
SESSION_DIR: str = "data/sessions"
UPLOAD_DIR: str = "data/uploads"
MAX_UPLOAD_SIZE_MB: int = 500

# ── Tracking ──────────────────────────────────────────────────────────────────
TRACK_THRESH: float = 0.4
TRACK_BUFFER: int = 30
MATCH_THRESH: float = 0.8
MOVEMENT_THRESHOLD_PX: float = 5.0    # Pixels movement to classify as moving

# ── Congestion Thresholds ──────────────────────────────────────────────────────
CONGESTION_THRESHOLDS: Dict[str, float] = {
    "LOW": 0.3,
    "MODERATE": 0.55,
    "HIGH": 0.75,
    # >= HIGH -> CRITICAL
}
