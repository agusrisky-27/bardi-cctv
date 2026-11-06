"""
Factory module for instantiating video source adapters.
"""

from __future__ import annotations

import logging
from rcis.config.settings import CameraConfig
from rcis.video.base import BaseVideoSource
from rcis.video.file_source import FileVideoSource
from rcis.video.rtsp_source import RTSPSource
from rcis.video.webcam_source import WebcamSource

logger = logging.getLogger("rcis.video.factory")


def create_video_source(config: CameraConfig) -> BaseVideoSource:
    """
    Instantiate concrete BaseVideoSource according to CameraConfig.
    """
    if config.source_type == "file":
        logger.info("Creating FileVideoSource for %s", config.file.path)
        return FileVideoSource(
            file_path=config.file.path,
            loop=config.file.loop,
            start_frame=config.file.start_frame,
        )
    elif config.source_type == "webcam":
        logger.info("Creating WebcamSource for device index %d", config.webcam.device_index)
        return WebcamSource(
            device_index=config.webcam.device_index,
            desired_fps=config.webcam.desired_fps,
            desired_width=config.webcam.desired_width,
            desired_height=config.webcam.desired_height,
        )
    elif config.source_type == "rtsp":
        logger.info("Creating RTSPSource")
        return RTSPSource(
            rtsp_url=config.rtsp.url,
            timeout_sec=config.rtsp.timeout_sec,
            reconnect_delay_sec=config.rtsp.reconnect_delay_sec,
            max_reconnect_attempts=config.rtsp.max_reconnect_attempts,
            buffer_size=config.rtsp.buffer_size,
        )
    else:
        raise ValueError(f"Unsupported video source_type: {config.source_type}")
