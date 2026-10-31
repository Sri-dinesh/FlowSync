"""
YOLOv8 inference engine with async-safe thread pool offloading.
Handles both fine-tuned custom model and COCO pretrained fallback.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import threading
import time
from typing import List, Optional

import numpy as np

from ..models.config import (
    COCO_TO_UNIFIED,
    VEHICLE_CLASSES,
    YOLO_CONF_THRESHOLD,
    YOLO_IMGSZ,
    YOLO_NMS_IOU,
    YOLO_ONNX_PATH,
    YOLO_PRETRAINED_PATH,
    YOLO_PRODUCTION_PATH,
    USE_ONNX,
)
from ..models.schemas import BoundingBox, VehicleDetection


def vehicle_taxonomy(names):
    """Map model-declared labels to the project taxonomy, never infer from path."""
    if isinstance(names,list):
        names = dict(enumerate(names))
    if not isinstance(names,dict) or any(type(k) is not int or k < 0 or not isinstance(v,str) for k,v in names.items()):
        raise ValueError("Detector model must declare an integer-indexed label taxonomy")
    accepted = set(VEHICLE_CLASSES.values())
    mapping = {index:name.strip().lower() for index,name in names.items() if name.strip().lower() in accepted}
    if not mapping:
        raise ValueError("Detector model declares no recognized vehicle classes")
    return mapping


@dataclass(frozen=True)
class _LoadedDetector:
    model: object
    device: str
    path: str
    classes: dict


class YOLODetector:
    """
    YOLOv8 vehicle detector.

    Supports:
    - Custom fine-tuned model (.pt) with 7 unified vehicle classes
    - COCO pretrained model (.pt) as fallback (5 vehicle classes, no auto_rickshaw)
    - ONNX artifacts when requested and available; speed is not established here.

    Blocking model calls are serialized; loaded model/taxonomy publish together.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        use_onnx: bool = USE_ONNX,
    ) -> None:
        if type(use_onnx) is not bool:
            raise ValueError("use_onnx must be boolean")
        self._loaded: Optional[_LoadedDetector] = None
        self._requested_path = model_path
        self._use_onnx = use_onnx
        self._inference_lock = threading.Lock()
        self._last_inference_ms: float = 0.0

    async def load_model(self, model_path: Optional[str] = None) -> None:
        """
        Load or hot-swap model. model_path can be .pt or .onnx.
        Falls back to COCO pretrained if production model not found.
        """
        path = model_path or self._requested_path

        if path is None:
            # Try production first, then pretrained fallback
            import os
            if self._use_onnx and os.path.exists(YOLO_ONNX_PATH):
                path = YOLO_ONNX_PATH
            elif os.path.exists(YOLO_PRODUCTION_PATH):
                path = YOLO_PRODUCTION_PATH
            elif os.path.exists(YOLO_PRETRAINED_PATH):
                path = YOLO_PRETRAINED_PATH
            else:
                # Download pretrained
                path = "yolov8n.pt"  # ultralytics auto-downloads

        def _load():
            from ultralytics import YOLO
            model = YOLO(path)
            # Detect device
            import torch
            if torch.cuda.is_available():
                device = "cuda:0"
            else:
                device = "cpu"
            return _LoadedDetector(model,device,str(path),vehicle_taxonomy(model.names))

        loaded = await asyncio.to_thread(_load)
        self._loaded = loaded
        self._requested_path = str(path)

    async def detect(self, frame: np.ndarray) -> VehicleDetection:
        """
        Main inference: frame -> VehicleDetection with all bboxes.
        Returns empty VehicleDetection if model not loaded.
        """
        if self._loaded is None:
            return VehicleDetection(
                frame_id=0,
                timestamp_ms=time.time() * 1000,
                bboxes=[],
                inference_time_ms=0.0,
                frame_width=frame.shape[1] if frame is not None else 640,
                frame_height=frame.shape[0] if frame is not None else 640,
                model_not_loaded=True,
            )

        start_ms = time.time() * 1000
        bboxes = await asyncio.to_thread(self._run_inference, frame)
        elapsed_ms = time.time() * 1000 - start_ms
        self._last_inference_ms = elapsed_ms

        return VehicleDetection(
            frame_id=0,
            timestamp_ms=time.time() * 1000,
            bboxes=bboxes,
            inference_time_ms=elapsed_ms,
            frame_width=frame.shape[1],
            frame_height=frame.shape[0],
        )

    def _run_inference(self, frame: np.ndarray) -> List[BoundingBox]:
        """Blocking inference — called via asyncio.to_thread()."""
        with self._inference_lock:
            loaded = self._loaded
            results = loaded.model(frame,conf=YOLO_CONF_THRESHOLD,iou=YOLO_NMS_IOU,imgsz=YOLO_IMGSZ,verbose=False)
            return self._filter_vehicle_classes(results,loaded.classes)

    def _filter_vehicle_classes(self, results, classes) -> List[BoundingBox]:
        """
        Use the taxonomy captured with this inference's model instance.
        """
        bboxes = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]

                if cls_id not in classes:
                    continue
                class_name = classes[cls_id]
                unified_id = next(k for k,v in VEHICLE_CLASSES.items() if v == class_name)

                bboxes.append(BoundingBox(
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    confidence=conf,
                    class_id=unified_id,
                    class_name=class_name,
                ))
        return bboxes

    async def warmup(self) -> float:
        """Run 3 dummy inferences to warm up. Returns avg latency ms."""
        if self._loaded is None:
            return 0.0
        dummy_frame = np.zeros((640, 640, 3), dtype=np.uint8)
        latencies = []
        for _ in range(3):
            start = time.time()
            await asyncio.to_thread(self._run_inference, dummy_frame)
            latencies.append((time.time() - start) * 1000)
        return sum(latencies) / len(latencies)

    @property
    def is_loaded(self) -> bool:
        return self._loaded is not None

    @property
    def model_path(self) -> Optional[str]:
        return self._loaded.path if self._loaded else self._requested_path

    @property
    def device(self) -> str:
        return self._loaded.device if self._loaded else "cpu"

    @property
    def is_custom_model(self) -> bool:
        """Legacy flag describes label mapping, not proof of fine-tuning."""
        return bool(self._loaded and self._loaded.classes != COCO_TO_UNIFIED)
