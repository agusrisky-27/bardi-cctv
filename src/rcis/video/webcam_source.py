"""
Webcam video source adapter for built-in or USB connected cameras.
"""

from __future__ import annotations

import logging
import time
from typing import Optional
import cv2

from rcis.video.base import BaseVideoSource, FrameData, VideoMetadata

logger = logging.getLogger("rcis.video.webcam")


class WebcamSource(BaseVideoSource):
    """
    Adapter for local webcam video capture devices.
    """

    def __init__(
        self,
        device_index: int = 0,
        desired_fps: int = 30,
        desired_width: int = 1280,
        desired_height: int = 720,
    ) -> None:
        self.device_index = device_index
        self.desired_fps = desired_fps
        self.desired_width = desired_width
        self.desired_height = desired_height
        self._cap: Optional[cv2.VideoCapture] = None
        self._current_frame_index = 0
        self._start_time: Optional[float] = None
        self._cached_metadata: Optional[VideoMetadata] = None

    def open(self) -> bool:
        logger.info("Opening webcam device index: %d", self.device_index)
        self._cap = cv2.VideoCapture(self.device_index)

        if not self._cap.isOpened():
            logger.error("Failed to open webcam at index: %d", self.device_index)
            return False

        # Request desired resolution and FPS
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.desired_width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.desired_height)
        self._cap.set(cv2.CAP_PROP_FPS, self.desired_fps)

        # Read actual acquired properties
        width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(self._cap.get(cv2.CAP_PROP_FPS))
        if fps <= 0:
            fps = float(self.desired_fps)

        self._cached_metadata = VideoMetadata(
            width=width,
            height=height,
            fps=fps,
            total_frames=-1,  # Live stream has unbounded frame count
            source_uri=f"webcam://{self.device_index}",
        )
        self._start_time = time.time()
        self._current_frame_index = 0

        logger.info(
            "Webcam active: index=%d (%dx%d @ %.1f FPS)",
            self.device_index,
            width,
            height,
            fps,
        )
        return True

    def read(self) -> Optional[FrameData]:
        if self._cap is None or not self._cap.isOpened():
            return None

        success, frame = self._cap.read()
        if not success or frame is None:
            logger.warning("Failed to grab frame from webcam index %d", self.device_index)
            return None

        current_time = time.time()
        elapsed = current_time - (self._start_time or current_time)

        frame_data = FrameData(
            frame_index=self._current_frame_index,
            timestamp_sec=elapsed,
            frame=frame,
            is_valid=True,
        )
        self._current_frame_index += 1
        return frame_data

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            logger.info("Released webcam device index %d", self.device_index)

    def is_opened(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    @property
    def metadata(self) -> VideoMetadata:
        if self._cached_metadata is None:
            return VideoMetadata(
                width=0,
                height=0,
                fps=0.0,
                total_frames=-1,
                source_uri=f"webcam://{self.device_index}",
            )
        return self._cached_metadata
