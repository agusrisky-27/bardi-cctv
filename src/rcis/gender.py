"""
Gender estimate per track: aggregate statistics only.

Privacy: body crops exist only in memory for one inference call and are never
written to disk. Only the voted label (male / female / None) and its confidence
are kept, and only until the track ends.
"""

from __future__ import annotations

from collections import deque
import logging
from pathlib import Path
from typing import Deque, Dict, Optional, Sequence, Tuple

import numpy as np
import supervision as sv

from rcis.config.settings import ModelsConfig

logger = logging.getLogger("rcis.gender")


def aggregate_votes(
    history: Sequence[np.ndarray], names: Sequence[str], min_votes: int, min_conf: float
) -> Tuple[Optional[str], Optional[float]]:
    """Mean probability over frames. Too few votes or low confidence -> label None (unknown)."""
    if len(history) < min_votes:
        return None, None
    mean = np.mean(history, axis=0)
    idx = int(mean.argmax())
    conf = float(mean[idx])
    return (names[idx] if conf >= min_conf else None), round(conf, 3)


class GenderVoter:
    def __init__(self, cfg: ModelsConfig, device: str) -> None:
        self.cfg = cfg
        self.device = device
        self.available = False
        self._model = None
        self.names: list[str] = []
        self._history: Dict[int, Deque[np.ndarray]] = {}
        self._n = 0
        path = Path(cfg.gender_path)
        if not path.exists():
            logger.warning("Gender weights not found at %s: gender estimate disabled (train in Colab).", path)
            return
        from ultralytics import YOLO

        self._model = YOLO(str(path))
        self.names = [str(n).lower() for _, n in sorted(self._model.names.items())]
        self.available = True
        logger.info("Gender classifier loaded: %s (classes: %s)", path, self.names)

    def update(self, frame: np.ndarray, detections: sv.Detections) -> None:
        """Classify a subset of tracks this frame (spread over frames) and store their probabilities."""
        if not self.available or len(detections) == 0 or detections.tracker_id is None:
            return
        self._n += 1
        frame_h = frame.shape[0]
        crops, tids = [], []
        for xyxy, tid in zip(detections.xyxy, detections.tracker_id):
            x1, y1, x2, y2 = (int(v) for v in xyxy)
            if (y2 - y1) < self.cfg.gender_min_height_ratio * frame_h:
                continue  # too small to classify reliably
            if (int(tid) + self._n) % self.cfg.gender_every_n:
                continue
            crop = frame[max(y1, 0):y2, max(x1, 0):x2]
            if crop.size:
                crops.append(crop)
                tids.append(int(tid))
        if not crops:
            return
        results = self._model.predict(crops, imgsz=self.cfg.gender_input_size, device=self.device, verbose=False)
        for tid, res in zip(tids, results):
            hist = self._history.setdefault(tid, deque(maxlen=self.cfg.gender_max_history))
            hist.append(res.probs.data.cpu().numpy())
        # crops go out of scope here: nothing is saved

    def pop(self, track_id: int) -> Tuple[Optional[str], Optional[float]]:
        """Final voted result for a finished track; frees its memory."""
        hist = self._history.pop(track_id, None)
        if not hist:
            return None, None
        return aggregate_votes(list(hist), self.names, self.cfg.gender_min_votes, self.cfg.gender_min_confidence)
