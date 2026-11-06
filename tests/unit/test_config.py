"""
Unit tests for configuration schemas and YAML loading.
"""

from pathlib import Path
import pytest
from pydantic import ValidationError

from rcis.config.settings import (
    AppConfig,
    CameraConfig,
    DetectionConfig,
    FileSourceConfig,
    TrackingConfig,
    VisualizationConfig,
)


def test_default_config_instantiation():
    config = AppConfig()
    assert config.camera.source_type == "file"
    assert config.detection.model_name == "yolo11n.pt"
    assert config.detection.confidence_threshold == 0.35
    assert config.detection.target_classes == [0]
    assert config.tracking.tracker_type == "bytetrack"
    assert config.visualization.show_bounding_boxes is True


def test_config_validation_constraints():
    # Confidence threshold must be within [0.0, 1.0]
    with pytest.raises(ValidationError):
        DetectionConfig(confidence_threshold=1.5)

    with pytest.raises(ValidationError):
        DetectionConfig(confidence_threshold=-0.1)

    # Input size must be >= 320
    with pytest.raises(ValidationError):
        DetectionConfig(input_size=100)


def test_load_from_yaml_files(tmp_path: Path):
    camera_yaml = tmp_path / "camera.yaml"
    camera_yaml.write_text(
        """
camera:
  id: "test_cam"
  source_type: "file"
  file:
    path: "test_video.mp4"
    loop: true
"""
    )

    detection_yaml = tmp_path / "detection.yaml"
    detection_yaml.write_text(
        """
detection:
  confidence_threshold: 0.45
  device: "cpu"
tracking:
  lost_track_buffer_frames: 45
"""
    )

    loaded = AppConfig.load(
        camera_config_path=camera_yaml,
        detection_config_path=detection_yaml,
    )

    assert loaded.camera.id == "test_cam"
    assert loaded.camera.file.loop is True
    assert loaded.camera.file.path == "test_video.mp4"
    assert loaded.detection.confidence_threshold == 0.45
    assert loaded.detection.device == "cpu"
    assert loaded.tracking.lost_track_buffer_frames == 45
