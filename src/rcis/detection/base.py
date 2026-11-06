"""
Abstract interface for object detection engines.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np
import supervision as sv


class BaseDetector(ABC):
    """
    Abstract interface for object detectors.
    """

    @abstractmethod
    def detect(self, frame: np.ndarray) -> sv.Detections:
        """
        Execute detection on a single frame (BGR numpy array).
        Returns a supervision.Detections instance with xyxy, confidence, and class_id.
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier or weights filename."""
        pass

    @property
    @abstractmethod
    def device(self) -> str:
        """Inference device (e.g. 'mps', 'cpu', 'cuda')."""
        pass
