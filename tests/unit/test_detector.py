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
