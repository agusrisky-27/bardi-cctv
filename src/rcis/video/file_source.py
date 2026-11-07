"""
Video file source adapter for processing recorded video files (.mp4, .avi, .mkv).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional
import cv2
import numpy as np

from rcis.video.base import BaseVideoSource, FrameData, VideoMetadata

logger = logging.getLogger("rcis.video.file")


class FileVideoSource(BaseVideoSource):
    """
    Adapter for reading stored video files.
    """

    def __init__(
        self,
        file_path: str | Path,
        loop: bool = False,
        start_frame: int = 0,
    ) -> None:
        self.file_path = Path(file_path)
        self.loop = loop
        self._loop_offset_sec = 0.0  # keeps timestamps increasing across loops
        self.start_frame = max(0, start_frame)
        self._cap: Optional[cv2.VideoCapture] = None
        self._current_frame_index = 0
        self._cached_metadata: Optional[VideoMetadata] = None

    def open(self) -> bool:
        if not self.file_path.exists():
            logger.error("Video file not found: %s", self.file_path.resolve())
            return False

        self._cap = cv2.VideoCapture(str(self.file_path.resolve()))
        if not self._cap.isOpened():
            logger.error("Failed to open video file: %s", self.file_path)
            return False

        width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(self._cap.get(cv2.CAP_PROP_FPS))
        if fps <= 0:
            fps = 25.0  # Fallback standard CCTV framerate
        total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))

        self._cached_metadata = VideoMetadata(
            width=width,
            height=height,
            fps=fps,
            total_frames=total_frames,
            source_uri=str(self.file_path),
        )

        if self.start_frame > 0:
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, self.start_frame)
            self._current_frame_index = self.start_frame
        else:
            self._current_frame_index = 0

        logger.info(
            "Opened video file: %s (%dx%d, %.1f FPS, %d frames)",
            self.file_path.name,
            width,
            height,
            fps,
            total_frames,
        )
        return True

    def read(self) -> Optional[FrameData]:
        if self._cap is None or not self._cap.isOpened():
            return None

        success, frame = self._cap.read()
        if not success or frame is None:
            if self.loop:
                logger.info("Looping video source: %s", self.file_path.name)
                self._loop_offset_sec += self._current_frame_index / (self.metadata.fps or 25.0)
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self._current_frame_index = 0
                success, frame = self._cap.read()
                if not success or frame is None:
                    return None
            else:
                logger.info("Reached end of video stream: %s", self.file_path.name)
                return None

        fps = self.metadata.fps if self._cached_metadata else 25.0
        timestamp_sec = self._loop_offset_sec + self._current_frame_index / fps

        frame_data = FrameData(
            frame_index=self._current_frame_index,
            timestamp_sec=timestamp_sec,
            frame=frame,
            is_valid=True,
        )
        self._current_frame_index += 1
        return frame_data

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            logger.info("Closed video file source: %s", self.file_path.name)

    def is_opened(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    @property
    def metadata(self) -> VideoMetadata:
        if self._cached_metadata is None:
            return VideoMetadata(
                width=0,
                height=0,
                fps=0.0,
                total_frames=0,
                source_uri=str(self.file_path),
            )
        return self._cached_metadata
