"""
Integration tests for the end-to-end VideoAnalyticsPipeline.
"""

from pathlib import Path
import cv2
import numpy as np
import pytest

from rcis.config.settings import AppConfig
from rcis.pipeline import VideoAnalyticsPipeline
from rcis.video.file_source import FileVideoSource


def create_synthetic_test_video(path: Path, num_frames: int = 30) -> None:
    """
    Generate a synthetic video test pattern with an animated rectangle.
    """
    width, height = 640, 480
    fps = 30.0
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(path.resolve()), fourcc, fps, (width, height))

    for i in range(num_frames):
        # Gray background
        frame = np.full((height, width, 3), 120, dtype=np.uint8)

        # Draw a moving high-contrast object
        x = 50 + (i * 5)
        y = 100 + (i * 2)
        cv2.rectangle(frame, (x, y), (x + 80, y + 160), (20, 20, 20), -1)
        # Add head circle
        cv2.circle(frame, (x + 40, y - 20), 20, (30, 30, 30), -1)

        out.write(frame)

    out.release()


def test_end_to_end_pipeline(tmp_path: Path):
    video_path = tmp_path / "test_synthetic.mp4"
    output_video_path = tmp_path / "annotated_output.mp4"

    create_synthetic_test_video(video_path, num_frames=20)
    assert video_path.exists()

    config = AppConfig()
    config.camera.source_type = "file"
    config.camera.file.path = str(video_path)
    config.detection.device = "mps" if pytest.importorskip("torch").backends.mps.is_available() else "cpu"
    config.detection.confidence_threshold = 0.25

    pipeline = VideoAnalyticsPipeline(config=config)
    summary = pipeline.run(
        display=False,
        output_path=output_video_path,
        max_frames=20,
    )

    # Verify summary metrics
    assert "fps" in summary
    assert "inference_ms" in summary
    assert "tracking_ms" in summary
    assert "memory_rss_mb" in summary
    assert summary["total_frames"] == 20

    # Verify annotated video output
    assert output_video_path.exists()
    assert output_video_path.stat().st_size > 0
