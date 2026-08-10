"""
YOLOTrainer — YOLOv8 fine-tuning orchestrator.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Dict

from ..models.schemas import TrainingConfig, TrainingResult


class YOLOTrainer:
    """
    Orchestrates YOLOv8 fine-tuning on the merged Indian traffic dataset.

    Training strategy:
    - Start from YOLOv8n pretrained on COCO (transfer learning)
    - Fine-tune all layers (dataset large enough)
    - Use SGD with cosine LR schedule
    - Early stopping with patience=15 epochs
    - Save best checkpoint based on val mAP50-95
    """

    def __init__(self, config: TrainingConfig) -> None:
        self.config = config

    def get_training_args(self) -> Dict:
        """Returns ultralytics training args dict."""
        return {
            "data": "data/processed/dataset.yaml",
            "epochs": self.config.epochs,
            "imgsz": self.config.image_size,
            "batch": self.config.batch_size,
            "device": self.config.device,
            "pretrained": True,
            "optimizer": "SGD",
            "lr0": self.config.learning_rate,
            "lrf": 0.01,
            "momentum": 0.937,
            "weight_decay": 0.0005,
            "warmup_epochs": 3,
            "warmup_momentum": 0.8,
            "cos_lr": True,
            "patience": self.config.patience,
            "save_period": 10,
            "amp": self.config.amp,
            "augment": self.config.augment,
            "project": "models/yolo/checkpoints",
            "name": "indian_traffic_v1",
            "exist_ok": False,
        }

    def train(self, dataset_yaml: str, output_dir: str = "models/yolo/checkpoints") -> TrainingResult:
        """Run YOLO training."""
        try:
            from ultralytics import YOLO
        except ImportError:
            raise ImportError("ultralytics not installed. Run: pip install ultralytics")

        start_time = time.time()
        model = YOLO(self.config.pretrained_weights)
        args = self.get_training_args()
        args["data"] = dataset_yaml
        args["project"] = output_dir

        results = model.train(**args)

        # Auto-copy best.pt to production
        best_path = Path(output_dir) / "indian_traffic_v1" / "weights" / "best.pt"
        if best_path.exists():
            prod_dir = Path("models/yolo/production")
            prod_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(best_path, prod_dir / "best.pt")
            print(f"[YOLOTrainer] Best model copied to models/yolo/production/best.pt")

        elapsed = time.time() - start_time

        # Extract metrics
        try:
            best_map50 = float(results.results_dict.get("metrics/mAP50(B)", 0.0))
            best_map50_95 = float(results.results_dict.get("metrics/mAP50-95(B)", 0.0))
        except Exception:
            best_map50 = 0.0
            best_map50_95 = 0.0

        # Save training metrics
        metrics_path = Path(output_dir) / "training_metrics.json"
        metrics_data = {
            "best_map50": best_map50,
            "best_map50_95": best_map50_95,
            "training_time_seconds": elapsed,
            "config": self.config.model_dump(),
        }
        with open(metrics_path, "w") as f:
            json.dump(metrics_data, f, indent=2)

        return TrainingResult(
            best_map50=best_map50,
            best_map50_95=best_map50_95,
            total_epochs=self.config.epochs,
            model_path=str(best_path),
            training_time_seconds=elapsed,
        )

    def resume(self, checkpoint_path: str) -> TrainingResult:
        """Resume training from a checkpoint."""
        from ultralytics import YOLO
        model = YOLO(checkpoint_path)
        args = self.get_training_args()
        args["resume"] = True
        results = model.train(**args)
        return TrainingResult(model_path=checkpoint_path)
