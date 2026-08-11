"""
Albumentations augmentation pipeline tailored for Indian traffic in varied conditions.
"""
from __future__ import annotations

import random
from typing import Dict, List, Tuple

import numpy as np

try:
    import albumentations as A
    ALBUMENTATIONS_AVAILABLE = True
except ImportError:
    ALBUMENTATIONS_AVAILABLE = False


def get_train_augmentation_pipeline():
    """
    Training augmentation pipeline for Indian traffic detection.
    Covers: spatial transforms, lighting/color, weather simulation, occlusion.
    """
    if not ALBUMENTATIONS_AVAILABLE:
        raise ImportError("albumentations not installed. Run: pip install albumentations")

    return A.Compose([
        # Spatial transforms
        A.HorizontalFlip(p=0.5),
        A.RandomRotate90(p=0.2),
        A.ShiftScaleRotate(shift_limit=0.0625, scale_limit=0.1, rotate_limit=15, p=0.5),

        # Lighting/color — critical for Indian conditions (harsh sun, night, rain)
        A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=0.5),
        A.HueSaturationValue(hue_shift_limit=10, sat_shift_limit=20, val_shift_limit=20, p=0.3),
        A.RandomGamma(gamma_limit=(80, 120), p=0.3),
        A.CLAHE(clip_limit=4.0, p=0.2),  # Enhance low-contrast (night/overcast)

        # Weather simulation
        A.RandomRain(slant_lower=-10, slant_upper=10, drop_length=15, p=0.15),
        A.RandomFog(fog_coef_lower=0.1, fog_coef_upper=0.3, p=0.1),  # Morning fog
        A.RandomSunFlare(p=0.1),              # Harsh Indian sun lens flare
        A.GaussNoise(var_limit=(10, 50), p=0.2),  # CCTV compression noise

        # Occlusion simulation (vehicles blocking each other at intersections)
        A.CoarseDropout(max_holes=3, max_height=50, max_width=50, p=0.2),

        # Resolution normalization
        A.Resize(640, 640),
    ], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels']))


def get_val_augmentation_pipeline():
    """Validation pipeline — only resize, no augmentation."""
    if not ALBUMENTATIONS_AVAILABLE:
        raise ImportError("albumentations not installed.")
    return A.Compose([
        A.Resize(640, 640),
    ], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels']))


def visualize_augmented_samples(image_dir: str, n: int = 10) -> None:
    """
    Visualize n augmented samples for sanity checking.
    Saves annotated images to augmentation_samples/ directory.
    """
    import os
    from pathlib import Path
    try:
        import cv2
    except ImportError:
        print("OpenCV not installed. Cannot visualize.")
        return

    pipeline = get_train_augmentation_pipeline()
    image_files = list(Path(image_dir).glob("*.jpg"))[:n]

    os.makedirs("augmentation_samples", exist_ok=True)
    for i, img_path in enumerate(image_files):
        img = cv2.imread(str(img_path))
        if img is None:
            continue
        result = pipeline(image=img, bboxes=[], class_labels=[])
        out_path = f"augmentation_samples/aug_{i:03d}.jpg"
        cv2.imwrite(out_path, result["image"])
        print(f"Saved: {out_path}")
