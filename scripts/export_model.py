#!/usr/bin/env python3
"""
Export trained YOLO model to ONNX for faster CPU inference.

Usage:
    python scripts/export_model.py --model models/yolo/production/best.pt --verify
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "server"))


def main():
    parser = argparse.ArgumentParser(
        description="Export FlowSync YOLO model to ONNX format."
    )
    parser.add_argument(
        "--model", type=str, default="models/yolo/production/best.pt",
        help="Path to .pt model file"
    )
    parser.add_argument(
        "--output", type=str, default="models/yolo/production/best.onnx",
        help="Output ONNX path"
    )
    parser.add_argument(
        "--opset", type=int, default=17, help="ONNX opset version"
    )
    parser.add_argument(
        "--verify", action="store_true", help="Verify ONNX vs PyTorch output"
    )
    parser.add_argument(
        "--benchmark", action="store_true", help="Benchmark PyTorch vs ONNX FPS"
    )
    args = parser.parse_args()

    if not Path(args.model).exists():
        print(f"ERROR: Model not found: {args.model}")
        sys.exit(1)

    from app.realworld.training.exporter import ModelExporter

    exporter = ModelExporter()
    print(f"[Export] Exporting {args.model} -> {args.output}")
    exported_path = exporter.export_onnx(args.model, args.output, opset=args.opset)

    if args.verify or args.benchmark:
        import numpy as np
        dummy_frame = (np.random.rand(640, 640, 3) * 255).astype("uint8")

    if args.verify:
        ok = exporter.verify_onnx(args.model, exported_path, dummy_frame)
        print(f"[Export] Verification: {'PASSED' if ok else 'FAILED'}")

    if args.benchmark:
        results = exporter.benchmark_comparison(args.model, exported_path)
        print(f"[Export] Benchmark:")
        print(f"  PyTorch FPS:  {results['pt_fps']}")
        print(f"  ONNX FPS:     {results['onnx_fps']}")
        print(f"  Speedup:      {results['speedup_ratio']}x")
        if results["speedup_ratio"] > 1.5:
            print("[Export] \u2713 ONNX speedup > 1.5x. Set USE_ONNX=True in config.py")
        else:
            print("[Export] ! Speedup < 1.5x. Keep PyTorch inference.")


if __name__ == "__main__":
    main()
