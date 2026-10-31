"""Detector metadata tests use fake models, never download weights or videos."""
import asyncio
import sys
from types import SimpleNamespace

import pytest
import torch

from app.realworld.pipeline import yolo_detector as detector_module
from app.realworld.pipeline.video_processor import VideoProcessor


def test_hot_swap_uses_actual_label_names_and_failed_load_keeps_identity(monkeypatch):
    names = {"custom.pt":{0:"truck",1:"auto_rickshaw"},
        "coco.pt":{0:"person",1:"bicycle",2:"car",3:"motorcycle",5:"bus",7:"truck"},
        "wrong.pt":{0:"person"}}
    monkeypatch.setitem(sys.modules,"ultralytics",SimpleNamespace(YOLO=lambda path:SimpleNamespace(names=names[path])))
    monkeypatch.setattr(torch.cuda,"is_available",lambda:False)
    detector = detector_module.YOLODetector()
    asyncio.run(detector.load_model("custom.pt"))
    assert detector.model_path == "custom.pt" and detector.is_custom_model
    box = SimpleNamespace(cls=torch.tensor([0]),conf=torch.tensor([.9]),xyxy=torch.tensor([[1,2,3,4]]))
    boxes = detector._filter_vehicle_classes([SimpleNamespace(boxes=[box])],detector._loaded.classes)
    assert boxes[0].class_name == "truck" and boxes[0].class_id == 6
    asyncio.run(detector.load_model("coco.pt"))
    assert not detector.is_custom_model
    loaded = detector._loaded
    with pytest.raises(ValueError,match="recognized"):
        asyncio.run(detector.load_model("wrong.pt"))
    assert detector._loaded is loaded and detector.model_path == "coco.pt"


def test_onnx_preference_selects_available_artifact_without_claiming_speed(tmp_path,monkeypatch):
    paths = [tmp_path/name for name in ("best.onnx","best.pt","pretrained.pt")]
    for path in paths:
        path.write_bytes(b"metadata fixture, not weights")
    for name,path in zip(("YOLO_ONNX_PATH","YOLO_PRODUCTION_PATH","YOLO_PRETRAINED_PATH"),paths):
        monkeypatch.setattr(detector_module,name,str(path))
    monkeypatch.setitem(sys.modules,"ultralytics",SimpleNamespace(YOLO=lambda _:SimpleNamespace(names={0:"car"})))
    monkeypatch.setattr(torch.cuda,"is_available",lambda:False)
    detector = detector_module.YOLODetector(use_onnx=True)
    asyncio.run(detector.load_model())
    assert detector.model_path == str(paths[0])
    other = detector_module.YOLODetector(use_onnx=False)
    asyncio.run(other.load_model())
    assert other.model_path == str(paths[1])


@pytest.mark.parametrize("fps",[0,-1,float("nan"),float("inf"),True])
def test_invalid_processing_rate_fails_before_opening_source(fps):
    with pytest.raises(ValueError,match="FPS"):
        VideoProcessor("unused.mp4",target_fps=fps)
