"""
Unit tests for ROIManager in app/realworld/pipeline/roi_manager.py
"""
import pytest
from app.realworld.pipeline.roi_manager import ROIManager
from app.realworld.models.schemas import BoundingBox, ROIConfig, ROIPolygon, VehicleDetection


def test_roi_manager_count_vehicles(tmp_path):
    roi_mgr = ROIManager(roi_config_dir=str(tmp_path))

    # Define a 2D square ROI for north_straight: relative coords [0.0, 0.0] to [0.5, 0.5]
    roi_north = ROIPolygon(
        lane_id="north_straight",
        vertices=[(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)],
    )

    config = ROIConfig(
        intersection_id="test_int",
        camera_id="cam0",
        frame_width=640,
        frame_height=480,
        rois=[roi_north],
    )

    # Vehicle 1: bottom-center (100, 100) -> rel (100/640=0.156, 100/480=0.208) -> inside
    bbox1 = BoundingBox(
        x1=80.0, y1=50.0, x2=120.0, y2=100.0,
        confidence=0.9, class_id=2, class_name="car"
    )

    # Vehicle 2: bottom-center (500, 400) -> rel (0.78, 0.83) -> outside
    bbox2 = BoundingBox(
        x1=480.0, y1=350.0, x2=520.0, y2=400.0,
        confidence=0.85, class_id=2, class_name="car"
    )

    detection = VehicleDetection(
        frame_id=1,
        timestamp_ms=1000.0,
        bboxes=[bbox1, bbox2],
        frame_width=640,
        frame_height=480,
    )

    raw, weighted, breakdown = roi_mgr.count_vehicles_per_lane(detection, config)

    assert raw.north_straight == 1
    assert raw.south_straight == 0
    assert breakdown.car == 2


def test_roi_manager_save_and_load(tmp_path):
    roi_mgr = ROIManager(roi_config_dir=str(tmp_path))
    roi_north = ROIPolygon(
        lane_id="north_straight",
        vertices=[(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)],
    )
    config = ROIConfig(
        intersection_id="int_save_test",
        camera_id="cam1",
        frame_width=640,
        frame_height=480,
        rois=[roi_north],
    )

    roi_mgr.save_config(config)

    loaded = roi_mgr.load_config("int_save_test", "cam1")
    assert loaded is not None
    assert loaded.intersection_id == "int_save_test"
    assert len(loaded.rois) == 1
    assert loaded.rois[0].lane_id == "north_straight"
