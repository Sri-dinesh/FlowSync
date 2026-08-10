#!/usr/bin/env python3
"""
Dataset downloader for FlowSync CCTV training.

Usage:
    python scripts/download_datasets.py --roboflow-key YOUR_KEY --datasets roboflow ua_detrac
"""
import argparse
import os
import sys
from pathlib import Path

# Add server to path
sys.path.insert(0, str(Path(__file__).parent.parent / "server"))


def download_ua_detrac(output_dir: Path) -> None:
    """Download UA-DETRAC dataset."""
    print("[UA-DETRAC] Download from: http://detrac-db.rit.albany.edu/")
    print("[UA-DETRAC] Note: Manual download required (no API). Download and extract to:")
    print(f"  {output_dir / 'ua_detrac'}")
    print("[UA-DETRAC] Files needed: DETRAC-Train-Annotations-XML.zip + DETRAC-train-data.zip")


def download_roboflow_datasets(api_key: str, dataset_ids: list, output_dir: Path) -> None:
    """Download Roboflow Indian traffic datasets."""
    try:
        from roboflow import Roboflow
    except ImportError:
        print("[Roboflow] Install: pip install roboflow")
        return

    rf = Roboflow(api_key=api_key)
    roboflow_dir = output_dir / "roboflow"
    roboflow_dir.mkdir(parents=True, exist_ok=True)

    DEFAULT_DATASETS = [
        ("krishnakant-patel", "indian-vehicle-detection", 1),
        ("project", "auto-rickshaw-detection", 1),
        ("two-wheeler-detection", "two-wheeler-detection", 1),
    ]

    for workspace, project_name, version in DEFAULT_DATASETS:
        try:
            project = rf.workspace(workspace).project(project_name)
            dataset = project.version(version).download("yolov8", location=str(roboflow_dir / project_name))
            print(f"[Roboflow] Downloaded: {project_name}")
        except Exception as e:
            print(f"[Roboflow] Failed {project_name}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Download datasets for FlowSync CCTV vehicle detection training."
    )
    parser.add_argument("--roboflow-key", type=str, default="", help="Roboflow API key")
    parser.add_argument(
        "--datasets", nargs="+",
        choices=["idd", "roboflow", "ua_detrac", "mio_tcd"],
        default=["roboflow", "ua_detrac"],
        help="Datasets to download",
    )
    parser.add_argument("--output", type=str, default="data/raw", help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[Downloader] Output directory: {output_dir.resolve()}")

    if "ua_detrac" in args.datasets:
        download_ua_detrac(output_dir)

    if "roboflow" in args.datasets:
        if not args.roboflow_key:
            print("[Roboflow] ERROR: --roboflow-key required for Roboflow download")
            sys.exit(1)
        download_roboflow_datasets(args.roboflow_key, [], output_dir)

    if "idd" in args.datasets:
        print("[IDD] Manual download required at: https://idd.insaan.iiit.ac.in/")
        print(f"[IDD] Extract to: {output_dir / 'idd'}")

    if "mio_tcd" in args.datasets:
        print("[MIO-TCD] Download at: http://podoce.dinf.usherbrooke.ca/challenge/dataset/")
        print(f"[MIO-TCD] Extract to: {output_dir / 'mio_tcd'}")

    print("[Downloader] Done.")


if __name__ == "__main__":
    main()
