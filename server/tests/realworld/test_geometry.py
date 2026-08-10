"""
Unit tests for geometric utilities in app/realworld/utils/geometry.py
"""
import pytest
import numpy as np
from app.realworld.utils.geometry import (
    point_in_polygon,
    get_bbox_center,
    get_bbox_bottom_center,
    bbox_iou_with_roi,
    normalize_polygon_to_frame,
    denormalize_polygon_from_frame,
)


def test_point_in_polygon_square():
    # 10x10 square from (0,0) to (10,10)
    square = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    assert point_in_polygon((5.0, 5.0), square) is True
    assert point_in_polygon((0.0, 0.0), square) is True
    assert point_in_polygon((15.0, 5.0), square) is False
    assert point_in_polygon((-1.0, 5.0), square) is False


def test_point_in_polygon_triangle():
    triangle = [(0.0, 0.0), (10.0, 0.0), (5.0, 10.0)]
    assert point_in_polygon((5.0, 2.0), triangle) is True
    assert point_in_polygon((0.0, 10.0), triangle) is False


def test_get_bbox_center():
    cx, cy = get_bbox_center(10.0, 20.0, 30.0, 40.0)
    assert cx == 20.0
    assert cy == 30.0


def test_get_bbox_bottom_center():
    bx, by = get_bbox_bottom_center(10.0, 20.0, 30.0, 40.0)
    assert bx == 20.0
    assert by == 40.0


def test_bbox_iou_with_roi():
    bbox = (0.0, 0.0, 10.0, 10.0)
    roi_poly = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
    iou = bbox_iou_with_roi(bbox[0], bbox[1], bbox[2], bbox[3], roi_poly)
    assert iou == pytest.approx(1.0, abs=1e-3)


def test_normalize_and_denormalize_polygon():
    rel_poly = [(0.1, 0.2), (0.5, 0.6)]
    px_poly = normalize_polygon_to_frame(rel_poly, 640, 480)
    assert px_poly == [(64.0, 96.0), (320.0, 288.0)]

    back_rel = denormalize_polygon_from_frame(px_poly, 640, 480)
    assert back_rel[0][0] == pytest.approx(0.1)
    assert back_rel[0][1] == pytest.approx(0.2)
