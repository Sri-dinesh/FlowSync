"""
YOLOv8 inference engine with async-safe thread pool offloading.
Handles both fine-tuned custom model and COCO pretrained fallback.
"""
from __future__ import annotations

import asyncio
import time
from typing import List, Optional

import numpy as np

from ..models.config import (
    COCO_TO_UNIFIED,
    VEHICLE_CLASSES,
    YOLO_CONF_THRESHOLD,
    YOLO_IMGSZ,
    YOLO_NMS_IOU,
    YOLO_PRETRAINED_PATH,
    YOLO_PRODUCTION_PATH,
    USE_ONNX,
)
from ..models.schemas import BoundingBox, VehicleDetection


class YOLODetector:
    """
    YOLOv8 vehicle detector.

    Supports:
    - Custom fine-tuned model (.pt) with 7 unified vehicle classes
    - COCO pretrained model (.pt) as fallback (5 vehicle classes, no auto_rickshaw)
    - ONNX Runtime model (.onnx) for 2-3x faster CPU inference

    Thread-safe for asyncio.to_thread() usage.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        use_onnx: bool = USE_ONNX,
    ) -> None:
        self._model = None
        self._model_path: Optional[str] = model_path
        self._use_onnx = use_onnx
        self._is_custom_model = False  # True after fine-tuning
        self._last_inference_ms: float = 0.0
        self._device: str = "cpu"

    async def load_model(self, model_path: Optional[str] = None) -> None:
        """
        Load or hot-swap model. model_path can be .pt or .onnx.
        Falls back to COCO pretrained if production model not found.
        """
        path = model_path or self._model_path

        if path is None:
            # Try production first, then pretrained fallback
            import os
            if os.path.exists(YOLO_PRODUCTION_PATH):
                path = YOLO_PRODUCTION_PATH
                self._is_custom_model = True
            elif os.path.exists(YOLO_PRETRAINED_PATH):
                path = YOLO_PRETRAINED_PATH
                self._is_custom_model = False
            else:
                # Download pretrained
                path = "yolov8n.pt"  # ultralytics auto-downloads
                self._is_custom_model = False

        self._model_path = path

        def _load():
            from ultralytics import YOLO
            model = YOLO(path)
            # Detect device
            import torch
            if torch.cuda.is_available():
                device = "cuda:0"
            else:
                device = "cpu"
            return model, device

        self._model, self._device = await asyncio.to_thread(_load)

    async def detect(self, frame: np.ndarray) -> VehicleDetection:
        """
        Main inference: frame -> VehicleDetection with all bboxes.
        Returns empty VehicleDetection if model not loaded.
        """
        if self._model is None:
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
        results = self._model(
            frame,
            conf=YOLO_CONF_THRESHOLD,
            iou=YOLO_NMS_IOU,
            imgsz=YOLO_IMGSZ,
            verbose=False,
        )
        return self._filter_vehicle_classes(results)

    def _filter_vehicle_classes(self, results) -> List[BoundingBox]:
        """
        Keep only vehicle class IDs, remap COCO IDs to unified IDs if using pretrained.
        """
        bboxes = []
        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0].tolist()]

                if self._is_custom_model:
                    # Custom model: class IDs are already 0-6 (unified)
                    if cls_id not in VEHICLE_CLASSES:
                        continue
                    class_name = VEHICLE_CLASSES[cls_id]
                    unified_id = cls_id
                else:
                    # COCO pretrained: remap vehicle COCO IDs to unified
                    if cls_id not in COCO_TO_UNIFIED:
                        continue
                    class_name = COCO_TO_UNIFIED[cls_id]
                    # Find unified ID from class name
                    unified_id = next(
                        (k for k, v in VEHICLE_CLASSES.items() if v == class_name), cls_id
                    )

                bboxes.append(BoundingBox(
                    x1=x1, y1=y1, x2=x2, y2=y2,
                    confidence=conf,
                    class_id=unified_id,
                    class_name=class_name,
                ))
        return bboxes

    async def warmup(self) -> float:
        """Run 3 dummy inferences to warm up. Returns avg latency ms."""
        if self._model is None:
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
        return self._model is not None

    @property
    def model_path(self) -> Optional[str]:
        return self._model_path

    @property
    def device(self) -> str:
        return self._device

    @property
    def is_custom_model(self) -> bool:
        return self._is_custom_model
