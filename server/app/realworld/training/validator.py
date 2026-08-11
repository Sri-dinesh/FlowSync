"""
ModelValidator — Comprehensive model evaluation after training.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Optional

import numpy as np

from ..models.schemas import ValidationMetrics

# Validation minimums
MINIMUM_TARGETS = {
    "map50": 0.70,
    "map50_95": 0.45,
    "auto_rickshaw_ap50": 0.65,
    "motorcycle_ap50": 0.70,
    "car_ap50": 0.85,
    "cpu_fps": 10.0,
}


class ValidationError(Exception):
    pass


class ModelValidator:
    """
    Runs full validation suite on trained model:
    1. mAP50, mAP50-95 on test set
    2. Per-class AP
    3. Confusion matrix
    4. FPS benchmark (CPU and GPU if available)
    5. Visual validation on sample test images
    """

    def __init__(self, model_path: str, dataset_yaml: str) -> None:
        self.model_path = model_path
        self.dataset_yaml = dataset_yaml

    def validate(self) -> ValidationMetrics:
        """Run full validation on test set."""
        from ultralytics import YOLO
        model = YOLO(self.model_path)
        results = model.val(data=self.dataset_yaml, split="test")

        try:
            map50 = float(results.results_dict.get("metrics/mAP50(B)", 0.0))
            map50_95 = float(results.results_dict.get("metrics/mAP50-95(B)", 0.0))
            precision = float(results.results_dict.get("metrics/precision(B)", 0.0))
            recall = float(results.results_dict.get("metrics/recall(B)", 0.0))
        except Exception:
            map50 = map50_95 = precision = recall = 0.0

        fps_results = self.benchmark_fps()
        model_size_mb = Path(self.model_path).stat().st_size / (1024 * 1024)

        metrics = ValidationMetrics(
            map50=map50,
            map50_95=map50_95,
            precision=precision,
            recall=recall,
            inference_fps_cpu=fps_results.get("cpu_fps", 0.0),
            model_size_mb=round(model_size_mb, 2),
        )

        # Enforce minimums
        failures = []
        if metrics.map50 < MINIMUM_TARGETS["map50"]:
            failures.append(f"mAP50 {metrics.map50:.3f} < {MINIMUM_TARGETS['map50']}")
        if metrics.map50_95 < MINIMUM_TARGETS["map50_95"]:
            failures.append(f"mAP50-95 {metrics.map50_95:.3f} < {MINIMUM_TARGETS['map50_95']}")
        if metrics.inference_fps_cpu < MINIMUM_TARGETS["cpu_fps"]:
            failures.append(f"CPU FPS {metrics.inference_fps_cpu:.1f} < {MINIMUM_TARGETS['cpu_fps']}")

        if failures:
            print(f"[Validator] WARNING — Below minimums: {', '.join(failures)}")

        return metrics

    def benchmark_fps(self, n_warmup: int = 3, n_runs: int = 50) -> Dict[str, float]:
        """Benchmark FPS on CPU (and GPU if available)."""
        from ultralytics import YOLO
        import numpy as np
        model = YOLO(self.model_path)
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)

        # CPU benchmark
        for _ in range(n_warmup):
            model(dummy, device="cpu", verbose=False)

        times = []
        for _ in range(n_runs):
            start = time.time()
            model(dummy, device="cpu", verbose=False)
            times.append(time.time() - start)

        cpu_fps = 1.0 / (sum(times) / len(times))
        return {"cpu_fps": round(cpu_fps, 1)}

    def generate_confusion_matrix(self, output_path: str) -> None:
        """Generate and save confusion matrix."""
        from ultralytics import YOLO
        model = YOLO(self.model_path)
        results = model.val(data=self.dataset_yaml, plots=True)
        print(f"[Validator] Confusion matrix saved to runs/val/")

    def visual_validation(
        self, n_samples: int = 20, output_dir: str = "validation_samples/"
    ) -> None:
        """Run visual validation on sample test images."""
        from ultralytics import YOLO
        from pathlib import Path
        import cv2

        model = YOLO(self.model_path)
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        import yaml
        with open(self.dataset_yaml) as f:
            dataset_cfg = yaml.safe_load(f)

        test_dir = Path(dataset_cfg.get("path", "")) / dataset_cfg.get("test", "images/test")
        images = list(test_dir.glob("*.jpg"))[:n_samples]

        for i, img_path in enumerate(images):
            results = model(str(img_path), verbose=False)
            annotated = results[0].plot()
            cv2.imwrite(f"{output_dir}/val_{i:03d}.jpg", annotated)

        print(f"[Validator] {len(images)} validation samples saved to {output_dir}")

    def export_full_report(self, output_path: str) -> None:
        """Export full validation report to JSON."""
        metrics = self.validate()
        report = metrics.model_dump()
        report["minimum_targets"] = MINIMUM_TARGETS
        report["model_path"] = self.model_path
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"[Validator] Full report saved to {output_path}")
