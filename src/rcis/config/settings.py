"""
Configuration management for RCIS using Pydantic schemas.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Literal, Optional
import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger("rcis.config")


class FileSourceConfig(BaseModel):
    path: str = "data/videos/sample.mp4"
    loop: bool = False
    start_frame: int = 0


class WebcamSourceConfig(BaseModel):
    device_index: int = 0
    desired_fps: int = 30
    desired_width: int = 1280
    desired_height: int = 720


class RTSPSourceConfig(BaseModel):
    url: str = ""
    timeout_sec: int = 10
    reconnect_delay_sec: int = 5
    max_reconnect_attempts: int = 10
    buffer_size: int = 1


class CameraConfig(BaseModel):
    id: str = "camera_01"
    name: str = "Default Camera"
    description: str = "Restaurant Surveillance Feed"
    source_type: Literal["file", "webcam", "rtsp"] = "file"
    file: FileSourceConfig = Field(default_factory=FileSourceConfig)
    webcam: WebcamSourceConfig = Field(default_factory=WebcamSourceConfig)
    rtsp: RTSPSourceConfig = Field(default_factory=RTSPSourceConfig)


class DetectionConfig(BaseModel):
    model_name: str = "yolo11n.pt"
    model_path: str = "models/yolo11n.pt"
    device: Literal["mps", "cpu", "cuda"] = "mps"
    target_classes: List[int] = Field(default_factory=lambda: [0])  # 0 = person
    confidence_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.50, ge=0.0, le=1.0)
    input_size: int = Field(default=640, ge=320, le=1920)
    half_precision: bool = False


class TrackingConfig(BaseModel):
    tracker_type: Literal["bytetrack"] = "bytetrack"
    track_activation_threshold: float = Field(default=0.30, ge=0.0, le=1.0)
    lost_track_buffer_frames: int = Field(default=30, ge=1, le=300)
    minimum_matching_threshold: float = Field(default=0.80, ge=0.0, le=1.0)
    minimum_consecutive_frames: int = Field(default=3, ge=1, le=30)
    trajectory_history_length: int = Field(default=60, ge=5, le=500)


class VisualizationConfig(BaseModel):
    show_bounding_boxes: bool = True
    show_track_ids: bool = True
    show_confidences: bool = True
    show_footpoints: bool = True
    show_trajectories: bool = True
    show_telemetry_hud: bool = True
    box_thickness: int = 2
    text_scale: float = 0.5


class AppConfig(BaseModel):
    camera: CameraConfig = Field(default_factory=CameraConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    tracking: TrackingConfig = Field(default_factory=TrackingConfig)
    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)

    @classmethod
    def load(
        cls,
        camera_config_path: Optional[str | Path] = None,
        detection_config_path: Optional[str | Path] = None,
    ) -> AppConfig:
        """
        Load application configuration from YAML files with graceful fallbacks.
        """
        config_data = {}

        if camera_config_path:
            c_path = Path(camera_config_path)
            if c_path.exists():
                try:
                    with open(c_path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                        if "camera" in data:
                            config_data["camera"] = data["camera"]
                except Exception as e:
                    logger.warning("Failed to load camera config from %s: %s", c_path, e)

        if detection_config_path:
            d_path = Path(detection_config_path)
            if d_path.exists():
                try:
                    with open(d_path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                        for section in ("detection", "tracking", "visualization"):
                            if section in data:
                                config_data[section] = data[section]
                except Exception as e:
                    logger.warning("Failed to load detection config from %s: %s", d_path, e)

        return cls(**config_data)
