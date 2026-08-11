#!/usr/bin/env python3
"""
Validate trained YOLO model.

Usage:
    python scripts/validate_model.py --model models/yolo/production/best.pt --report
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "server"))


def main():
    parser = argparse.ArgumentParser(description="Validate FlowSync YOLO model.")
    parser.add_argument("--model", type=str, default="models/yolo/production/best.pt")
    parser.add_argument("--dataset", type=str, default="data/processed/dataset.yaml")
    parser.add_argument("--report", action="store_true", help="Export full validation report")
    parser.add_argument("--visual", action="store_true", help="Generate visual validation samples")
    args = parser.parse_args()

    if not Path(args.model).exists():
        print(f"ERROR: Model not found: {args.model}")
        sys.exit(1)

    from app.realworld.training.validator import ModelValidator

    validator = ModelValidator(model_path=args.model, dataset_yaml=args.dataset)

    print(f"[Validate] Running validation: {args.model}")
    metrics = validator.validate()

    print(f"\n[Validate] Results:")
    print(f"  mAP50:      {metrics.map50:.3f}")
    print(f"  mAP50-95:   {metrics.map50_95:.3f}")
    print(f"  Precision:  {metrics.precision:.3f}")
    print(f"  Recall:     {metrics.recall:.3f}")
    print(f"  CPU FPS:    {metrics.inference_fps_cpu:.1f}")
    print(f"  Size (MB):  {metrics.model_size_mb:.1f}")

    if args.report:
        report_path = "models/yolo/production/validation_report.json"
        validator.export_full_report(report_path)
        print(f"[Validate] Report saved: {report_path}")

    if args.visual:
        validator.visual_validation(n_samples=20)


if __name__ == "__main__":
    main()
