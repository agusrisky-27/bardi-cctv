"""
RTSP IP camera video source adapter with reconnection resilience.
"""

from __future__ import annotations

import logging
import os
import threading
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
        self._latest = None
        self._lock = threading.Lock()
        self._new_frame = threading.Event()
        self._stop = threading.Event()
        self._failed = False
        self._thread: Optional[threading.Thread] = None

    def _mask_url_credentials(self, url: str) -> str:
        """Strip username/password from RTSP URL for log safety."""
        if "@" in url and "://" in url:
            prefix, remainder = url.split("://", 1)
            credentials, host_path = remainder.split("@", 1)
            return f"{prefix}://***:***@{host_path}"
        return url

    def _connect(self) -> bool:
        """Open the capture once and refresh metadata."""
        masked = self._mask_url_credentials(self.rtsp_url)
        logger.info("Connecting to RTSP stream: %s", masked)
        # TCP avoids smeared frames on Wi-Fi cameras; small buffer keeps latency low
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
            f"rtsp_transport;tcp|buffer_size;{self.buffer_size * 1024}|timeout;{self.timeout_sec * 1_000_000}"
        )
        cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            logger.error("Could not establish RTSP connection to %s", masked)
            cap.release()
            return False

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        self._cached_metadata = VideoMetadata(
            width=width, height=height, fps=fps if fps > 0 else 25.0, total_frames=-1, source_uri=masked
        )
        self._cap = cap
        logger.info("Connected to RTSP stream: %s (%dx%d @ %.1f FPS)", masked, width, height, fps)
        return True

    def open(self) -> bool:
        if not self.rtsp_url:
            logger.error("RTSP URL is empty or unconfigured.")
            return False
        if not self._connect():
            return False
        self._start_time = time.time()
        self._current_frame_index = 0
        self._stop.clear()
        self._failed = False
        self._thread = threading.Thread(target=self._grab_loop, name="rtsp-grabber", daemon=True)
        self._thread.start()
        return True

    def _grab_loop(self) -> None:
        """Background reader: always keep only the newest frame so analysis never lags behind live."""
        attempt = 0
        while not self._stop.is_set():
            ok, frame = (False, None) if self._cap is None else self._cap.read()
            if ok and frame is not None:
                attempt = 0
                with self._lock:
                    self._latest = frame
                self._new_frame.set()
                continue

            if self._cap is not None:
                self._cap.release()
                self._cap = None
            attempt += 1
            if self.max_reconnect_attempts > 0 and attempt > self.max_reconnect_attempts:
                logger.error("Exceeded maximum RTSP reconnection attempts.")
                self._failed = True
                self._new_frame.set()  # wake read() so it can stop
                return
            delay = min(self.reconnect_delay_sec * 2 ** (attempt - 1), 60)  # exponential backoff
            logger.warning("RTSP stream lost. Reconnect %d in %ds...", attempt, delay)
            if self._stop.wait(delay):
                return
            self._connect()

    def read(self) -> Optional[FrameData]:
        # Wait for a frame newer than the last one returned (covers reconnect time too).
        while not self._stop.is_set() and not self._failed:
            if self._new_frame.wait(timeout=1.0):
                break
        if self._failed or self._stop.is_set():
            return None
        with self._lock:
            frame = self._latest
            self._new_frame.clear()

        frame_data = FrameData(
            frame_index=self._current_frame_index,
            timestamp_sec=time.time() - (self._start_time or time.time()),
            frame=frame,
            is_valid=True,
        )
        self._current_frame_index += 1
        return frame_data

    def release(self) -> None:
        self._stop.set()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=self.timeout_sec + 2)
            self._thread = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None
            logger.info("Released RTSP stream connection.")

    def is_opened(self) -> bool:
        # Stays "open" while reconnecting; only a stop or exhausted retries ends the stream.
        return self._thread is not None and not self._failed and not self._stop.is_set()

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
