"""
Base interfaces and data structures for video source adapters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generator, Optional, Tuple
import numpy as np


@dataclass(frozen=True)
class VideoMetadata:
    width: int
    height: int
    fps: float
    total_frames: int
    source_uri: str

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height if self.height > 0 else 0.0


@dataclass
class FrameData:
    frame_index: int
    timestamp_sec: float
    frame: np.ndarray
    is_valid: bool = True


class BaseVideoSource(ABC):
    """
    Abstract interface for video input sources (files, webcams, RTSP streams).
    """

    @abstractmethod
    def open(self) -> bool:
        """Initialize and open the video stream."""
        pass

    @abstractmethod
    def read(self) -> Optional[FrameData]:
        """Read the next available video frame."""
        pass

    @abstractmethod
    def release(self) -> None:
        """Release underlying video capture hardware/network buffers."""
        pass

    @abstractmethod
    def is_opened(self) -> bool:
        """Check whether the video stream is active."""
        pass

    @property
    @abstractmethod
    def metadata(self) -> VideoMetadata:
        """Return video stream metadata (resolution, fps, frame count)."""
        pass

    def frames(self) -> Generator[FrameData, None, None]:
        """
        Yield frames continuously until stream ends or is closed.
        """
        while self.is_opened():
            frame_data = self.read()
            if frame_data is None:
                break
            yield frame_data

    def __enter__(self) -> BaseVideoSource:
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.release()
