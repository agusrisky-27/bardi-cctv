"""
YOLO-based person detection engine using Ultralytics.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional
import numpy as np
import supervision as sv
import torch
from ultralytics import YOLO

from rcis.config.settings import DetectionConfig
from rcis.detection.base import BaseDetector

logger = logging.getLogger("rcis.detection.yolo")


class YOLODetector(BaseDetector):
    """
    Ultralytics YOLO wrapper targeting human pedestrian detection.
    """

    def __init__(self, config: Optional[DetectionConfig] = None) -> None:
        self.config = config or DetectionConfig()
        self._device = self._resolve_device(self.config.device)
        self._model = self._load_model()

    def _resolve_device(self, requested_device: str) -> str:
        """
        Validate compute target and fallback to CPU if unavailable.
        """
        if requested_device == "mps":
            if torch.backends.mps.is_available():
                logger.info("Apple Silicon Metal (MPS) acceleration is ACTIVE.")
                return "mps"
            logger.warning("MPS requested but not available. Falling back to CPU.")
            return "cpu"
        elif requested_device == "cuda":
            if torch.cuda.is_available():
                logger.info("NVIDIA CUDA acceleration is ACTIVE.")
                return "cuda"
            logger.warning("CUDA requested but not available. Falling back to CPU.")
            return "cpu"
        return "cpu"

    def _load_model(self) -> YOLO:
        """
        Load YOLO model weights. Checks local path first, otherwise downloads.
        """
        model_path = Path(self.config.model_path)
        if model_path.exists():
            target_source = str(model_path.resolve())
            logger.info("Loading YOLO weights from local path: %s", target_source)
        else:
            target_source = self.config.model_name
            logger.info("Local weights not found at %s. Using default weights: %s", model_path, target_source)

        model = YOLO(target_source)
        model.to(self._device)
        logger.info("YOLO model '%s' loaded onto device '%s'", target_source, self._device)
        return model

    def detect(self, frame: np.ndarray) -> sv.Detections:
        """
        Run person detection on a frame (BGR image).
        """
        if frame is None or frame.size == 0:
            return sv.Detections.empty()

        # Run inference with Ultralytics
        results = self._model(
            frame,
            conf=self.config.confidence_threshold,
            iou=self.config.iou_threshold,
            imgsz=self.config.input_size,
            classes=self.config.target_classes,
            device=self._device,
            verbose=False,
        )

        if not results or len(results) == 0:
            return sv.Detections.empty()

        # Convert to supervision.Detections
        detections = sv.Detections.from_ultralytics(results[0])

        # Filter strictly by target classes if any non-target classes slipped through
        if len(detections) > 0 and detections.class_id is not None:
            mask = np.isin(detections.class_id, self.config.target_classes)
            detections = detections[mask]

        return detections

    @property
    def model_name(self) -> str:
        return self.config.model_name

    @property
    def device(self) -> str:
        return self._device
