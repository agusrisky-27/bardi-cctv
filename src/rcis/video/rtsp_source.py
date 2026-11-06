"""
RTSP IP camera video source adapter with reconnection resilience.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional
import cv2

from rcis.video.base import BaseVideoSource, FrameData, VideoMetadata

logger = logging.getLogger("rcis.video.rtsp")


class RTSPSource(BaseVideoSource):
    """
    Adapter for RTSP network video streams from IP surveillance cameras.
    """

    def __init__(
        self,
        rtsp_url: str,
        timeout_sec: int = 10,
        reconnect_delay_sec: int = 5,
        max_reconnect_attempts: int = 10,
        buffer_size: int = 1,
    ) -> None:
        self.rtsp_url = rtsp_url
        self.timeout_sec = timeout_sec
        self.reconnect_delay_sec = reconnect_delay_sec
        self.max_reconnect_attempts = max_reconnect_attempts
        self.buffer_size = buffer_size

        self._cap: Optional[cv2.VideoCapture] = None
        self._current_frame_index = 0
        self._start_time: Optional[float] = None
        self._cached_metadata: Optional[VideoMetadata] = None

    def _mask_url_credentials(self, url: str) -> str:
        """Strip username/password from RTSP URL for log safety."""
        if "@" in url and "://" in url:
            prefix, remainder = url.split("://", 1)
            credentials, host_path = remainder.split("@", 1)
            return f"{prefix}://***:***@{host_path}"
        return url

    def open(self) -> bool:
        if not self.rtsp_url:
            logger.error("RTSP URL is empty or unconfigured.")
            return False

        masked = self._mask_url_credentials(self.rtsp_url)
        logger.info("Connecting to RTSP stream: %s", masked)

        # Set network buffer size to minimize latency for live streams
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
            f"rtsp_transport;tcp|buffer_size;{self.buffer_size * 1024}"
        )

        self._cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        if not self._cap.isOpened():
            logger.error("Could not establish RTSP connection to %s", masked)
            return False

        width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(self._cap.get(cv2.CAP_PROP_FPS))
        if fps <= 0:
            fps = 25.0

        self._cached_metadata = VideoMetadata(
            width=width,
            height=height,
            fps=fps,
            total_frames=-1,
            source_uri=masked,
        )
        self._start_time = time.time()
        self._current_frame_index = 0
        logger.info("Connected to RTSP stream: %s (%dx%d @ %.1f FPS)", masked, width, height, fps)
        return True

    def read(self) -> Optional[FrameData]:
        if self._cap is None or not self._cap.isOpened():
            if not self._attempt_reconnect():
                return None

        success, frame = self._cap.read()
        if not success or frame is None:
            logger.warning("RTSP packet drop or stream disconnected. Attempting reconnect...")
            if not self._attempt_reconnect():
                return None
            success, frame = self._cap.read()
            if not success or frame is None:
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

    def _attempt_reconnect(self) -> bool:
        """Attempt to re-establish dropped RTSP connection."""
        self.release()
        for attempt in range(1, self.max_reconnect_attempts + 1):
            logger.info("Reconnection attempt %d/%d...", attempt, self.max_reconnect_attempts)
            time.sleep(self.reconnect_delay_sec)
            if self.open():
                logger.info("Successfully reconnected to RTSP stream.")
                return True
        logger.error("Exceeded maximum RTSP reconnection attempts.")
        return False

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            logger.info("Released RTSP stream connection.")

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
                source_uri=self._mask_url_credentials(self.rtsp_url),
            )
        return self._cached_metadata
