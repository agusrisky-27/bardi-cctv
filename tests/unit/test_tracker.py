"""
Unit tests for tracking abstraction and ByteTrackTracker.
"""

import numpy as np
import pytest
import supervision as sv

from rcis.config.settings import TrackingConfig
from rcis.tracking.base import calculate_footpoints
from rcis.tracking.byte_tracker import ByteTrackTracker


def test_calculate_footpoints():
    boxes = np.array([
        [100.0, 100.0, 200.0, 300.0],  # x1=100, y1=100, x2=200, y2=300 -> foot=(150, 300)
        [0.0, 0.0, 50.0, 80.0],        # x1=0, y1=0, x2=50, y2=80 -> foot=(25, 80)
    ], dtype=np.float32)

    footpoints = calculate_footpoints(boxes)
    assert footpoints.shape == (2, 2)
    assert np.allclose(footpoints[0], [150.0, 300.0])
    assert np.allclose(footpoints[1], [25.0, 80.0])

    empty_boxes = np.empty((0, 4), dtype=np.float32)
    empty_foot = calculate_footpoints(empty_boxes)
    assert empty_foot.shape == (0, 2)


def test_tracker_id_assignment_and_persistence():
    tracker = ByteTrackTracker(TrackingConfig())

    # Frame 1: Detection at (100, 100, 150, 200)
    det1 = sv.Detections(
        xyxy=np.array([[100, 100, 150, 200]], dtype=np.float32),
        confidence=np.array([0.95], dtype=np.float32),
        class_id=np.array([0], dtype=np.int32),
    )
    tracked1 = tracker.update(det1)
    assert len(tracked1) == 1
    assert tracked1.tracker_id is not None
    tid1 = tracked1.tracker_id[0]

    # Frame 2: Object moves slightly to (103, 102, 153, 202)
    det2 = sv.Detections(
        xyxy=np.array([[103, 102, 153, 202]], dtype=np.float32),
        confidence=np.array([0.94], dtype=np.float32),
        class_id=np.array([0], dtype=np.int32),
    )
    tracked2 = tracker.update(det2)
    assert len(tracked2) == 1
    assert tracked2.tracker_id is not None
    tid2 = tracked2.tracker_id[0]

    # Persistent tracking ID must match across consecutive frames
    assert tid1 == tid2

    # Check trajectory accumulation
    traj = tracker.get_trajectory(tid1)
    assert len(traj) == 2


def test_tracker_empty_update():
    tracker = ByteTrackTracker(TrackingConfig())
    empty_det = sv.Detections.empty()
    res = tracker.update(empty_det)
    assert len(res) == 0
