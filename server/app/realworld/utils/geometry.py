"""
Geometric utilities for ROI intersection logic.
Point-in-polygon, IoU, perspective transforms.
"""
from __future__ import annotations

import math
from typing import List, Optional, Tuple

import numpy as np

try:
    from shapely.geometry import Point, Polygon
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False


def point_in_polygon(point: Tuple[float, float], polygon: List[Tuple[float, float]]) -> bool:
    """
    Ray-casting algorithm.
    True if point (x,y) is inside polygon vertices list.
    """
    x, y = point
    n = len(polygon)
    if n < 3:
        return False
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def get_bbox_center(x1: float, y1: float, x2: float, y2: float) -> Tuple[float, float]:
    """Returns (cx, cy) center of bounding box."""
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def get_bbox_bottom_center(x1: float, y1: float, x2: float, y2: float) -> Tuple[float, float]:
    """Returns bottom-center of bbox — better for vehicle-in-lane detection (foot point)."""
    return ((x1 + x2) / 2.0, y2)


def bbox_iou_with_roi(
    x1: float, y1: float, x2: float, y2: float,
    roi_polygon: List[Tuple[float, float]]
) -> float:
    """
    Returns IoU between bbox and ROI polygon bounding rect.
    Uses shapely for accuracy if available, else falls back to rect IoU.
    """
    if SHAPELY_AVAILABLE:
        try:
            bbox_poly = Polygon([(x1, y1), (x2, y1), (x2, y2), (x1, y2)])
            roi_poly = Polygon(roi_polygon)
            if not roi_poly.is_valid or not bbox_poly.is_valid:
                return 0.0
            intersection = bbox_poly.intersection(roi_poly).area
            union = bbox_poly.union(roi_poly).area
            return float(intersection / union) if union > 0 else 0.0
        except Exception:
            pass

    # Fallback: bounding rect IoU
    roi_xs = [p[0] for p in roi_polygon]
    roi_ys = [p[1] for p in roi_polygon]
    rx1, ry1 = min(roi_xs), min(roi_ys)
    rx2, ry2 = max(roi_xs), max(roi_ys)

    ix1 = max(x1, rx1)
    iy1 = max(y1, ry1)
    ix2 = min(x2, rx2)
    iy2 = min(y2, ry2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0

    inter = (ix2 - ix1) * (iy2 - iy1)
    bbox_area = (x2 - x1) * (y2 - y1)
    roi_area = (rx2 - rx1) * (ry2 - ry1)
    union = bbox_area + roi_area - inter
    return float(inter / union) if union > 0 else 0.0


def normalize_polygon_to_frame(
    polygon: List[Tuple[float, float]],
    frame_width: int,
    frame_height: int,
) -> List[Tuple[float, float]]:
    """Converts polygon from relative [0-1] coords to pixel coords."""
    return [(x * frame_width, y * frame_height) for x, y in polygon]


def denormalize_polygon_from_frame(
    polygon: List[Tuple[float, float]],
    frame_width: int,
    frame_height: int,
) -> List[Tuple[float, float]]:
    """Converts polygon from pixel coords to relative [0-1] coords."""
    return [(x / frame_width, y / frame_height) for x, y in polygon]


def perspective_transform_point(
    point: Tuple[float, float],
    transform_matrix: np.ndarray,
) -> Tuple[float, float]:
    """Apply perspective homography matrix to a point (for bird's-eye view correction)."""
    pt = np.array([[point[0], point[1]]], dtype=np.float32).reshape(-1, 1, 2)
    transformed = cv2_perspective_transform(pt, transform_matrix)
    return float(transformed[0][0][0]), float(transformed[0][0][1])


def cv2_perspective_transform(pts: np.ndarray, M: np.ndarray) -> np.ndarray:
    """OpenCV-compatible perspective transform without importing cv2 here."""
    # pts shape: (N, 1, 2)
    pts_h = np.concatenate([pts.reshape(-1, 2), np.ones((pts.shape[0], 1))], axis=1)  # Nx3
    transformed = (M @ pts_h.T).T  # Nx3
    transformed = transformed[:, :2] / transformed[:, 2:3]  # normalize
    return transformed.reshape(-1, 1, 2)


def compute_homography_matrix(
    src_points: List[Tuple[float, float]],
    dst_points: List[Tuple[float, float]],
) -> np.ndarray:
    """
    Compute perspective homography matrix from 4 src → dst point pairs.
    Used for bird's-eye view correction of non-overhead CCTV cameras.
    """
    if len(src_points) != 4 or len(dst_points) != 4:
        raise ValueError("Exactly 4 point pairs required for homography.")
    src = np.array(src_points, dtype=np.float32)
    dst = np.array(dst_points, dtype=np.float32)
    # Simple DLT algorithm
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([-x, -y, -1, 0, 0, 0, u*x, u*y, u])
        A.append([0, 0, 0, -x, -y, -1, v*x, v*y, v])
    A = np.array(A, dtype=np.float64)
    _, _, Vt = np.linalg.svd(A)
    H = Vt[-1].reshape(3, 3)
    return H / H[2, 2]


def apply_bird_eye_transform(
    frame: np.ndarray,
    matrix: np.ndarray,
    output_size: Optional[Tuple[int, int]] = None,
) -> np.ndarray:
    """
    Apply perspective transformation (bird's-eye view) to a frame.
    Requires OpenCV.
    """
    try:
        import cv2
        h, w = frame.shape[:2]
        out_w, out_h = output_size if output_size else (w, h)
        return cv2.warpPerspective(frame, matrix, (out_w, out_h))
    except ImportError:
        raise RuntimeError("OpenCV not installed. Run: pip install opencv-python-headless")
