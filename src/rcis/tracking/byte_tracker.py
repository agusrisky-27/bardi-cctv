"""
ByteTrack tracker implementation adhering to the BaseTracker interface.
"""

from __future__ import annotations

from collections import deque
import logging
from types import SimpleNamespace
from typing import Deque, Dict, List, Optional, Tuple
import numpy as np
import supervision as sv
from ultralytics.trackers.byte_tracker import BYTETracker

from rcis.config.settings import TrackingConfig
from rcis.tracking.base import BaseTracker, calculate_footpoints

logger = logging.getLogger("rcis.tracking.byte")


class _DetectionProxy:
    """
    Lightweight adapter wrapping supervision.Detections for BYTETracker ingestion.
    """

    def __init__(self, xyxy: np.ndarray, conf: np.ndarray, cls: np.ndarray) -> None:
        self.xyxy = xyxy
        self.conf = conf
        self.cls = cls
        if len(xyxy) > 0:
            w = xyxy[:, 2] - xyxy[:, 0]
            h = xyxy[:, 3] - xyxy[:, 1]
            x_c = xyxy[:, 0] + w / 2.0
            y_c = xyxy[:, 1] + h / 2.0
            self.xywh = np.column_stack((x_c, y_c, w, h))
        else:
            self.xywh = np.empty((0, 4), dtype=np.float32)

    def __getitem__(self, idx: int | slice | np.ndarray) -> _DetectionProxy:
        return _DetectionProxy(self.xyxy[idx], self.conf[idx], self.cls[idx])

    def __len__(self) -> int:
        return len(self.xyxy)


class ByteTrackTracker(BaseTracker):
    """
    ByteTrack multi-object tracker wrapping the native Kalman-filter BYTETracker algorithm.
    """

    def __init__(self, config: Optional[TrackingConfig] = None) -> None:
        self.config = config or TrackingConfig()
        self._args = SimpleNamespace(
            tracker_type="bytetrack",
            track_high_thresh=self.config.track_activation_threshold,
            track_low_thresh=0.1,
            new_track_thresh=self.config.track_activation_threshold,
            track_buffer=self.config.lost_track_buffer_frames,
            match_thresh=self.config.minimum_matching_threshold,
            fuse_score=True,
        )
        self._tracker = BYTETracker(self._args)
        # Dictionary storing historical footpoint trajectories per track_id
        self._trajectories: Dict[int, Deque[Tuple[float, float]]] = {}
        self._max_history = self.config.trajectory_history_length

    def update(self, detections: sv.Detections) -> sv.Detections:
        """
        Ingest frame detections and assign temporal tracking IDs.
        """
        if len(detections) == 0:
            # Update tracker with empty detections to advance internal Kalman state
            proxy = _DetectionProxy(
                xyxy=np.empty((0, 4), dtype=np.float32),
                conf=np.empty((0,), dtype=np.float32),
                cls=np.empty((0,), dtype=np.int32),
            )
            self._tracker.update(proxy)
            return sv.Detections.empty()

        conf = detections.confidence if detections.confidence is not None else np.ones(len(detections))
        cls = detections.class_id if detections.class_id is not None else np.zeros(len(detections), dtype=np.int32)
        proxy = _DetectionProxy(xyxy=detections.xyxy, conf=conf, cls=cls)

        tracked_output = self._tracker.update(proxy)

        if len(tracked_output) == 0:
            return sv.Detections.empty()

        # Format: [x1, y1, x2, y2, track_id, score, cls, idx]
        xyxy = tracked_output[:, :4]
        track_ids = tracked_output[:, 4].astype(int)
        scores = tracked_output[:, 5]
        class_ids = tracked_output[:, 6].astype(int)

        # Update historical footpoints for active tracks
        footpoints = calculate_footpoints(xyxy)
        active_ids = set()
        for idx, tid in enumerate(track_ids):
            active_ids.add(tid)
            if tid not in self._trajectories:
                self._trajectories[tid] = deque(maxlen=self._max_history)
            fx, fy = float(footpoints[idx, 0]), float(footpoints[idx, 1])
            self._trajectories[tid].append((fx, fy))

        # Evict stale trajectories that are no longer in tracker's active or lost buffer
        all_tracker_ids = {
            t.track_id for t in (self._tracker.tracked_stracks + self._tracker.lost_stracks)
        }
        for tid in list(self._trajectories.keys()):
            if tid not in all_tracker_ids:
                del self._trajectories[tid]

        return sv.Detections(
            xyxy=xyxy,
            confidence=scores,
            class_id=class_ids,
            tracker_id=track_ids,
        )

    def get_trajectory(self, track_id: int) -> List[Tuple[float, float]]:
        """
        Retrieve footpoint trajectory for a given track ID.
        """
        if track_id in self._trajectories:
            return list(self._trajectories[track_id])
        return []

    def reset(self) -> None:
        """
        Reset internal Kalman filter and trajectory buffers.
        """
        self._tracker = BYTETracker(self._args)
        self._trajectories.clear()
        logger.info("ByteTrack tracker reset.")
