"""
Abstract interface and utilities for multi-object tracking.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple
import numpy as np
import supervision as sv


def calculate_footpoints(xyxy: np.ndarray) -> np.ndarray:
    """
    Calculate bottom-center anchor points (footpoints) from bounding boxes.
    xyxy format: array of shape (N, 4) -> [[x1, y1, x2, y2], ...]
    Returns array of shape (N, 2) -> [[x_foot, y_foot], ...]
    """
    if len(xyxy) == 0:
        return np.empty((0, 2), dtype=np.float32)

    x_center = (xyxy[:, 0] + xyxy[:, 2]) / 2.0
    y_bottom = xyxy[:, 3]
    return np.column_stack((x_center, y_bottom))


class BaseTracker(ABC):
    """
    Abstract interface for object tracking across video frames.
    """

    @abstractmethod
    def update(self, detections: sv.Detections) -> sv.Detections:
        """
        Update tracker state with new frame detections.
        Returns supervision.Detections with populated .tracker_id attribute.
        """
        pass

    @abstractmethod
    def get_trajectory(self, track_id: int) -> List[Tuple[float, float]]:
        """
        Return the historical footpoint path for a specific track ID.
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset internal tracker state."""
        pass
