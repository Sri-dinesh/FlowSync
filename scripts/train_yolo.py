#!/usr/bin/env python3
"""
Launch YOLOv8 fine-tuning run.

Usage:
    python scripts/train_yolo.py --epochs 100 --batch 16 --dataset data/processed/dataset.yaml
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "server"))


def main():
    parser = argparse.ArgumentParser(description="Train YOLO model for FlowSync vehicle detection.")
    parser.add_argument("--dataset", type=str, default="data/processed/dataset.yaml")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", type=str, default="auto")
    parser.add_argument("--model-size", type=str, default="yolov8n", choices=["yolov8n", "yolov8s", "yolov8m"])
    parser.add_argument("--output", type=str, default="models/yolo/checkpoints")
    args = parser.parse_args()

    if not Path(args.dataset).exists():
        print(f"ERROR: Dataset YAML not found: {args.dataset}")
        print("Run: python scripts/merge_datasets.py first")
        sys.exit(1)

    from app.realworld.models.schemas import TrainingConfig
    from app.realworld.training.trainer import YOLOTrainer

    config = TrainingConfig(
        model_size=args.model_size,
        epochs=args.epochs,
        batch_size=args.batch,
        image_size=args.imgsz,
        device=args.device,
        pretrained_weights=f"{args.model_size}.pt",
    )

    trainer = YOLOTrainer(config)
    print(f"[Train] Starting YOLOv8 training: {args.epochs} epochs, batch={args.batch}")
    result = trainer.train(dataset_yaml=args.dataset, output_dir=args.output)

    print(f"\n[Train] Complete!")
    print(f"  Best mAP50:    {result.best_map50:.3f}")
    print(f"  Best mAP50-95: {result.best_map50_95:.3f}")
    print(f"  Model saved:   {result.model_path}")
    print(f"  Time:          {result.training_time_seconds/60:.1f} minutes")


if __name__ == "__main__":
    main()
