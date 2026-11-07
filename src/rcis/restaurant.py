"""
Second detector for restaurant objects (plates/food, waiters).

Weights come from the Colab notebook (models/restaurant_detector.pt). A missing
file disables the feature. To try food-wait timing before training, point
`models.restaurant_path` at models/yolo11n.pt and set `food_classes` to COCO
names such as [bowl, cup, sandwich, pizza, cake] (see configs/detection.yaml).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Tuple

import numpy as np
import supervision as sv

from rcis.config.settings import ModelsConfig

logger = logging.getLogger("rcis.restaurant")


class RestaurantDetector:
    def __init__(self, cfg: ModelsConfig, device: str, imgsz: int = 640) -> None:
        self.cfg = cfg
        self.device = device
        self.imgsz = imgsz
        self.available = False
        self._model = None
        if not cfg.restaurant_path:
            logger.info("Restaurant detector off (restaurant_path empty): no food-wait / waiter detection.")
            return
        path = Path(cfg.restaurant_path)
        if not path.exists():
            logger.warning("Restaurant weights not found at %s: food-wait & waiter detection disabled.", path)
            return
        from ultralytics import YOLO

        self._model = YOLO(str(path))
        names = {int(i): str(n).lower() for i, n in self._model.names.items()}
        food, waiter = {c.lower() for c in cfg.food_classes}, {c.lower() for c in cfg.waiter_classes}
        self._food_ids = [i for i, n in names.items() if n in food]
        self._waiter_ids = [i for i, n in names.items() if n in waiter]
        if not (self._food_ids or self._waiter_ids):
            logger.warning("None of %s / %s found in model classes %s: restaurant detector disabled.",
                           sorted(food), sorted(waiter), sorted(names.values()))
            return
        self.available = True
        logger.info("Restaurant detector loaded: %s (food ids %s, waiter ids %s)",
                    path, self._food_ids, self._waiter_ids)

    def detect(self, frame: np.ndarray) -> Tuple[sv.Detections, sv.Detections]:
        """Return (food, waiters) detections for one frame."""
        res = self._model(frame, conf=self.cfg.restaurant_conf, imgsz=self.imgsz, device=self.device, verbose=False)
        det = sv.Detections.from_ultralytics(res[0])
        if len(det) == 0 or det.class_id is None:
            return sv.Detections.empty(), sv.Detections.empty()
        return det[np.isin(det.class_id, self._food_ids)], det[np.isin(det.class_id, self._waiter_ids)]
