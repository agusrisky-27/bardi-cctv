"""
Unit tests for video source adapters.
"""

from pathlib import Path
import cv2
import numpy as np
import pytest

from rcis.config.settings import CameraConfig
from rcis.video.base import BaseVideoSource, FrameData
from rcis.video.factory import create_video_source
from rcis.video.file_source import FileVideoSource


def test_file_video_source_non_existent():
    source = FileVideoSource("non_existent_file.mp4")
    assert not source.open()
    assert not source.is_opened()
    assert source.read() is None


def test_file_video_source_with_dummy_video(tmp_path: Path):
    video_path = tmp_path / "dummy.mp4"

    # Create a small 5-frame video
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(video_path), fourcc, 10.0, (100, 100))
    for i in range(5):
        frame = np.full((100, 100, 3), i * 50, dtype=np.uint8)
        out.write(frame)
    out.release()

    # Read with FileVideoSource context manager
    with FileVideoSource(video_path) as src:
        assert src.is_opened()
        meta = src.metadata
        assert meta.width == 100
        assert meta.height == 100
        assert meta.fps == 10.0
        assert meta.total_frames == 5

        frames_read = []
        for frame_data in src.frames():
            assert isinstance(frame_data, FrameData)
            assert frame_data.frame.shape == (100, 100, 3)
            frames_read.append(frame_data.frame_index)

        assert len(frames_read) == 5
        assert frames_read == [0, 1, 2, 3, 4]

    assert not src.is_opened()


def test_video_source_factory(tmp_path: Path):
    cfg = CameraConfig(source_type="file")
    cfg.file.path = str(tmp_path / "test.mp4")
    source = create_video_source(cfg)
    assert isinstance(source, FileVideoSource)
