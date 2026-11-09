"""
Unit tests for detection abstraction and YOLODetector.
"""

import numpy as np
import pytest
import supervision as sv

from rcis.config.settings import DetectionConfig
from rcis.detection.base import BaseDetector
from rcis.detection.yolo_detector import YOLODetector


def test_detector_initialization():
    config = DetectionConfig(model_path="models/yolo11n.pt", device="cpu")
    detector = YOLODetector(config)
    assert isinstance(detector, BaseDetector)
    assert detector.device == "cpu"
    assert detector.model_name == "yolo11n.pt"


def test_detector_empty_frame():
    detector = YOLODetector(DetectionConfig(model_path="models/yolo11n.pt", device="cpu"))
    empty_frame = np.empty((0, 0, 3), dtype=np.uint8)
    detections = detector.detect(empty_frame)
    assert isinstance(detections, sv.Detections)
    assert len(detections) == 0


def test_detector_blank_canvas():
    detector = YOLODetector(DetectionConfig(model_path="models/yolo11n.pt", device="cpu"))
    blank_frame = np.zeros((320, 320, 3), dtype=np.uint8)
    detections = detector.detect(blank_frame)
    assert isinstance(detections, sv.Detections)
    # A blank black canvas should yield 0 person detections
    assert len(detections) == 0


def test_missing_coreml_model_falls_back_to_pt(tmp_path):
    import shutil
    from pathlib import Path

    shutil.copy(Path(__file__).parents[2] / "models" / "yolo11n.pt", tmp_path / "yolo.pt")
    det = YOLODetector(DetectionConfig(model_path=str(tmp_path / "yolo.mlpackage"), device="cpu"))
    assert det._model.ckpt_path.endswith("yolo.pt")  # the deleted .mlpackage is replaced by the .pt next to it
