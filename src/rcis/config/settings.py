"""
Configuration management for RCIS using Pydantic schemas.
"""

from __future__ import annotations

import logging
import os
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


class AnalyticsConfig(BaseModel):
    """Thresholds for zone, dwell, sitting and visit analytics (all times in seconds)."""

    zones_path: str = "configs/zones.yaml"
    db_path: str = "data/rcis.db"
    exports_dir: str = "data/exports"
    frame_stride: int = Field(default=1, ge=1, le=30)  # process every Nth frame
    # Speed in "frame heights per second" so it is resolution independent
    sitting_max_speed: float = Field(default=0.03, ge=0.0)
    sitting_min_seconds: float = Field(default=10.0, ge=0.0)
    speed_window_seconds: float = Field(default=1.5, gt=0.0)
    visit_timeout_seconds: float = Field(default=5.0, gt=0.0)  # track unseen this long = left
    live_recent_seconds: float = Field(default=1.0, gt=0.0)  # dashboard "people now" = seen within this
    min_visit_seconds: float = Field(default=2.0, ge=0.0)  # shorter tracks are noise
    table_merge_gap_seconds: float = Field(default=20.0, ge=0.0)  # tolerate ID switches at a table
    heatmap_scale: float = Field(default=0.25, gt=0.0, le=1.0)
    heatmap_save_every_seconds: float = Field(default=60.0, gt=0.0)
    staff_min_tables: int = Field(default=3, ge=0)  # visits this many tables = staff, not customer; 0 = off
    staff_waiter_hits: int = Field(default=2, ge=1)  # waiter-detector overlaps before a track is staff
    food_confirm_seconds: float = Field(default=3.0, ge=0.0)  # plate must stay this long in a table zone
    # Laptop use (COCO class 63, no training needed). -1 disables the feature.
    laptop_class_id: int = Field(default=63, ge=-1)
    laptop_min_seconds: float = Field(default=5.0, ge=0.0)  # shorter sessions are ignored
    laptop_gap_seconds: float = Field(default=5.0, ge=0.0)  # tolerate missed laptop detections
    laptop_near_margin: float = Field(default=0.3, ge=0.0)  # expand person box by this fraction to find "their" laptop
    # DB backup to a cloud-synced folder (RCIS_BACKUP_DIR in .env, default data/backups). 0 = only at shutdown.
    backup_every_hours: float = Field(default=1.0, ge=0.0)


class ModelsConfig(BaseModel):
    """Optional Colab-trained weights. A missing file disables that feature (no crash)."""

    restaurant_path: str = "models/restaurant_detector.pt"
    restaurant_conf: float = Field(default=0.35, ge=0.0, le=1.0)
    restaurant_every_n: int = Field(default=3, ge=1)  # run every Nth processed frame
    food_classes: List[str] = Field(default_factory=lambda: ["plate_food"])
    waiter_classes: List[str] = Field(default_factory=lambda: ["waiter"])
    gender_path: str = "models/gender_classifier.pt"
    gender_input_size: int = Field(default=96, ge=32)
    gender_every_n: int = Field(default=3, ge=1)  # classify each track every Nth processed frame
    gender_min_height_ratio: float = Field(default=0.25, ge=0.0, le=1.0)  # bbox height / frame height
    gender_min_votes: int = Field(default=5, ge=1)
    gender_min_confidence: float = Field(default=0.65, ge=0.0, le=1.0)
    gender_max_history: int = Field(default=30, ge=1)


class SecurityConfig(BaseModel):
    """Alert rules. Telegram token/chat id come from .env (TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)."""

    alerts_dir: str = "data/alerts"  # only face-blurred snapshots are ever written here
    restricted_cooldown_seconds: float = Field(default=60.0, ge=0.0)
    loiter_seconds: float = Field(default=600.0, gt=0.0)  # present this long without sitting/laptop = loitering
    after_hours_cooldown_seconds: float = Field(default=600.0, ge=0.0)
    open_hour: Optional[int] = Field(default=None, ge=0, le=23)  # None = after-hours alert off
    close_hour: Optional[int] = Field(default=None, ge=0, le=23)
    head_blur_fraction: float = Field(default=0.25, gt=0.0, le=1.0)  # top part of a person box that is blurred


class AppConfig(BaseModel):
    camera: CameraConfig = Field(default_factory=CameraConfig)
    detection: DetectionConfig = Field(default_factory=DetectionConfig)
    tracking: TrackingConfig = Field(default_factory=TrackingConfig)
    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)
    analytics: AnalyticsConfig = Field(default_factory=AnalyticsConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)

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
                        for section in ("detection", "tracking", "visualization", "analytics", "models", "security"):
                            if section in data:
                                config_data[section] = data[section]
                except Exception as e:
                    logger.warning("Failed to load detection config from %s: %s", d_path, e)

        return cls(**config_data)


def load_dotenv(path: str = ".env") -> None:
    """Minimal .env reader (KEY=VALUE lines); real env vars win."""
    if not Path(path).exists():
        return
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.split(" #")[0].strip().strip('"').strip("'"))


def camera_rotation() -> int:
    """RCIS_CAMERA_ROTATE in .env: 180 when the camera is mounted upside down (tripod/ceiling), else 0."""
    value = int(os.environ.get("RCIS_CAMERA_ROTATE", "0") or 0)
    if value not in (0, 180):
        raise ValueError(f"RCIS_CAMERA_ROTATE must be 0 or 180, got {value}")
    return value
