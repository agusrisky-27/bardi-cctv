"""
Security alerts: restricted zone, loitering, people outside opening hours.

Privacy: a snapshot is written to disk or sent to Telegram only AFTER the head
region of every detected person has been blurred. No unblurred frame is stored.
"""

from __future__ import annotations

from datetime import datetime
import logging
import os
from pathlib import Path
import re
import threading
from typing import Callable, Dict, Optional, Set, Tuple

import cv2
import numpy as np
import supervision as sv

from rcis.analytics import RestaurantAnalytics
from rcis.config.settings import SecurityConfig
from rcis.storage import Storage

logger = logging.getLogger("rcis.security")
Sender = Callable[[str, bytes], None]  # (caption, jpeg bytes)


def blur_faces(frame: np.ndarray, person_xyxy: np.ndarray, head_fraction: float = 0.25) -> np.ndarray:
    """Return a copy with the head region (top `head_fraction` of each person box) Gaussian-blurred.

    shortcut: heads come from person boxes, not a face model (OpenCV 5 dropped Haar cascades).
    A person the detector missed stays visible; upgrade to YuNet (cv2.FaceDetectorYN) if that matters.
    """
    out = frame.copy()
    h, w = out.shape[:2]
    for x1, y1, x2, y2 in person_xyxy:
        bh = y2 - y1
        top, bottom = int(max(y1 - 0.05 * bh, 0)), int(min(y1 + head_fraction * bh, h))
        left, right = int(max(x1, 0)), int(min(x2, w))
        if bottom - top < 2 or right - left < 2:
            continue
        k = (max(right - left, bottom - top) // 3) | 1  # odd kernel, strong enough to hide a face
        out[top:bottom, left:right] = cv2.GaussianBlur(out[top:bottom, left:right], (max(k, 3), max(k, 3)), 0)
    return out


def telegram_sender_from_env() -> Optional[Sender]:
    token, chat_id = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return None

    def send(caption: str, jpeg: bytes) -> None:
        import requests

        r = requests.post(f"https://api.telegram.org/bot{token}/sendPhoto", data={"chat_id": chat_id, "caption": caption},
                          files={"photo": ("alert.jpg", jpeg, "image/jpeg")}, timeout=15)
        r.raise_for_status()

    return send


class Security:
    def __init__(self, cfg: SecurityConfig, storage: Optional[Storage] = None, sender: Optional[Sender] = None) -> None:
        self.cfg = cfg
        self.storage = storage
        self.sender = sender if sender is not None else telegram_sender_from_env()
        self._last: Dict[Tuple[str, str], float] = {}
        self._loiter_done: Set[int] = set()
        logger.info("Security alerts on. Telegram: %s", "ON" if self.sender else "off (no TELEGRAM_TOKEN/CHAT_ID)")

    def _after_hours(self, t: float) -> bool:
        o, c = self.cfg.open_hour, self.cfg.close_hour
        if o is None or c is None or o == c:
            return False
        hour = datetime.fromtimestamp(t).hour
        return not (o <= hour < c) if o < c else not (hour >= o or hour < c)  # o > c: open overnight

    def check(self, frame: np.ndarray, detections: sv.Detections, analytics: RestaurantAnalytics, t: float) -> None:
        persons = detections.xyxy if len(detections) else np.empty((0, 4))
        now = {tid: st for tid, st in analytics.tracks.items() if st.last_t == t}  # tracks seen this frame
        for z in analytics.zones:
            if z.kind == "restricted" and any(z.name in st.zones and not st.is_staff for st in now.values()):
                self._alert("restricted_zone", z.name, t, frame, persons,
                            f"Orang terdeteksi di zona terlarang '{z.name}'", self.cfg.restricted_cooldown_seconds)
        for tid, st in now.items():
            if (self.cfg.loiter_seconds and st.first_t not in self._loiter_done and t - st.first_t >= self.cfg.loiter_seconds and not st.sitting
                    and not st.is_staff and not analytics._laptop_active(st)):
                self._loiter_done.add(st.first_t)  # once per person; first_t survives tracker ID switches
                self._alert("loitering", next(iter(st.zones), None), t, frame, persons,
                            f"Seseorang berada di area ini lebih dari {self.cfg.loiter_seconds / 60:.0f} menit", 0)
        if now and self._after_hours(t):
            self._alert("after_hours", None, t, frame, persons, "Ada orang di luar jam operasional",
                        self.cfg.after_hours_cooldown_seconds)

    def _alert(self, kind: str, zone: Optional[str], t: float, frame: np.ndarray, persons: np.ndarray,
               text: str, cooldown: float) -> None:
        key = (kind, zone or "")
        if t - self._last.get(key, -1e18) < cooldown:
            return
        self._last[key] = t
        stamp = datetime.fromtimestamp(t)
        img = blur_faces(frame, persons, self.cfg.head_blur_fraction)
        cv2.putText(img, f"{kind} {stamp:%Y-%m-%d %H:%M:%S}", (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        folder = Path(self.cfg.alerts_dir)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{kind}_{re.sub(r'[^A-Za-z0-9_-]', '', zone or '')}_{stamp:%Y%m%d_%H%M%S}.jpg"
        cv2.imwrite(str(path), img)
        if self.storage is not None:
            self.storage.add_alert(kind, zone, t, str(path))
        logger.warning("ALERT %s (%s): %s", kind, zone or "-", path.name)
        ok, jpeg = cv2.imencode(".jpg", img)
        if self.sender is not None and ok:
            threading.Thread(target=self._send, args=(f"ALERT: {text} ({stamp:%H:%M:%S})", jpeg.tobytes()),
                             daemon=True).start()

    def _send(self, caption: str, jpeg: bytes) -> None:
        try:
            self.sender(caption, jpeg)
        except Exception as e:  # never log str(e): requests errors contain the bot token in the URL
            status = getattr(getattr(e, "response", None), "status_code", None)
            logger.warning("Telegram send failed: %s%s", type(e).__name__, f" (HTTP {status})" if status else "")
