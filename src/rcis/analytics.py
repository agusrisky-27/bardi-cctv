"""
Restaurant analytics on top of tracked detections:
door line in/out + entry side, polygon zones, dwell time, sitting status,
table sessions, and a footpoint heatmap.

All positions use the footpoint (bottom-center of the bbox), never the box center.
Timestamps are epoch seconds.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Deque, Dict, List, Optional, Set, Tuple

import cv2
import numpy as np
import supervision as sv
import yaml

from rcis.config.settings import AnalyticsConfig
from rcis.storage import Storage

logger = logging.getLogger("rcis.analytics")

ANCHOR = sv.Position.BOTTOM_CENTER
ZONE_COLORS = {  # BGR
    "table": (80, 200, 80),
    "door": (255, 180, 0),
    "cashier": (255, 120, 60),
    "queue": (0, 200, 255),
    "staff": (200, 120, 255),
    "restricted": (40, 40, 230),
    "area": (200, 200, 200),
}


@dataclass
class Zone:
    name: str
    kind: str
    polygon: np.ndarray  # (N, 2) int pixels
    detector: sv.PolygonZone


@dataclass
class TrackState:
    first_t: float
    last_t: float
    entry_side: str
    history: Deque[Tuple[float, float, float]] = field(default_factory=deque)  # (t, x, y)
    zones: Dict[str, float] = field(default_factory=dict)  # zone name -> enter time
    sat_in: Set[str] = field(default_factory=set)
    still_since: Optional[float] = None
    sitting: bool = False


def load_zones(path: str | Path, frame_w: int, frame_h: int) -> Tuple[List[Zone], Optional[sv.LineZone]]:
    """Load zones + door line from YAML and convert to pixel coordinates."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    scale = np.array([frame_w, frame_h], dtype=float)
    if data.get("coordinate_format", "normalized") == "absolute":
        scale = np.array([1.0, 1.0])

    def to_px(points) -> np.ndarray:
        return np.round(np.asarray(points, dtype=float) * scale).astype(np.int64)

    zones = []
    for z in data.get("zones", []):
        poly = to_px(z["polygon"])
        zones.append(Zone(z["name"], z.get("kind", "area"), poly, sv.PolygonZone(poly, triggering_anchors=(ANCHOR,))))

    line = None
    if data.get("door_line"):
        s, e = to_px([data["door_line"]["start"], data["door_line"]["end"]])
        line = sv.LineZone(
            start=sv.Point(int(s[0]), int(s[1])), end=sv.Point(int(e[0]), int(e[1])), triggering_anchors=(ANCHOR,)
        )
    return zones, line


class RestaurantAnalytics:
    def __init__(
        self,
        config: AnalyticsConfig,
        frame_wh: Tuple[int, int],
        zones: List[Zone],
        door_line: Optional[sv.LineZone] = None,
        storage: Optional[Storage] = None,
    ) -> None:
        self.cfg = config
        self.w, self.h = frame_wh
        self.zones = zones
        self.door_line = door_line
        self.storage = storage
        self.tracks: Dict[int, TrackState] = {}
        self.count_in = 0
        self.count_out = 0
        self.table_sessions: Dict[str, dict] = {}  # zone -> {"id", "seated_at", "last_occupied"}
        s = config.heatmap_scale
        self.heatmap = np.zeros((max(1, int(self.h * s)), max(1, int(self.w * s))), dtype=np.float32)
        self._bg_samples: List[np.ndarray] = []
        self._last_bg_t: Optional[float] = None
        self._last_save_t: Optional[float] = None

    # ------------------------------------------------------------------ update
    def _edge_side(self, x: float, y: float) -> str:
        """Side of the frame the track first appeared from (asal lintasan)."""
        dist = {"kiri": x / self.w, "kanan": 1 - x / self.w, "depan": 1 - y / self.h, "belakang": y / self.h}
        return min(dist, key=dist.get)

    def update(self, detections: sv.Detections, t: float, frame: Optional[np.ndarray] = None) -> None:
        if len(detections) and detections.tracker_id is not None:
            feet = detections.get_anchors_coordinates(ANCHOR)
            inside = {z.name: z.detector.trigger(detections) for z in self.zones}
            crossed_in, crossed_out = (
                self.door_line.trigger(detections) if self.door_line else (None, None)
            )
            for i, tid in enumerate(detections.tracker_id):
                tid = int(tid)
                x, y = float(feet[i, 0]), float(feet[i, 1])
                st = self.tracks.get(tid)
                if st is None:
                    st = self.tracks[tid] = TrackState(first_t=t, last_t=t, entry_side=self._edge_side(x, y))
                st.last_t = t
                st.history.append((t, x, y))
                self._update_motion(st, t)
                self._update_zones(tid, st, {n: bool(m[i]) for n, m in inside.items()}, t)
                self._add_heat(x, y)
                if crossed_in is not None and crossed_in[i]:
                    self.count_in += 1
                    self._store("add_line_crossing", tid, "in", st.entry_side, t)
                if crossed_out is not None and crossed_out[i]:
                    self.count_out += 1
                    self._store("add_line_crossing", tid, "out", st.entry_side, t)

        self._expire(t)
        self._update_tables(t)
        if frame is not None:
            self._sample_background(frame, t)
        if self._last_save_t is None or t - self._last_save_t >= self.cfg.heatmap_save_every_seconds:
            self._last_save_t = t
            self.save_heatmap()

    def _update_motion(self, st: TrackState, t: float) -> None:
        """Mark a track 'still' when its footpoint barely moves over the speed window."""
        while len(st.history) > 2 and t - st.history[0][0] > self.cfg.speed_window_seconds:
            st.history.popleft()
        t0, x0, y0 = st.history[0]
        span = t - t0
        if span < self.cfg.speed_window_seconds * 0.5:
            return  # not enough history yet, keep previous state
        speed = float(np.hypot(st.history[-1][1] - x0, st.history[-1][2] - y0)) / self.h / span
        if speed <= self.cfg.sitting_max_speed:
            st.still_since = st.still_since if st.still_since is not None else t0
        else:
            st.still_since = None

    def _update_zones(self, tid: int, st: TrackState, inside: Dict[str, bool], t: float) -> None:
        for z in self.zones:
            if inside[z.name] and z.name not in st.zones:
                st.zones[z.name] = t
            elif not inside[z.name] and z.name in st.zones:
                self._close_zone(tid, st, z.name, t)
        st.sitting = (
            st.still_since is not None
            and t - st.still_since >= self.cfg.sitting_min_seconds
            and any(z.kind == "table" and z.name in st.zones for z in self.zones)
        )
        if st.sitting:
            st.sat_in.update(z.name for z in self.zones if z.kind == "table" and z.name in st.zones)

    def _close_zone(self, tid: int, st: TrackState, name: str, t: float) -> None:
        enter_t = st.zones.pop(name)
        self._store("add_zone_event", tid, name, enter_t, t, name in st.sat_in)
        st.sat_in.discard(name)

    def _update_tables(self, t: float) -> None:
        """One session per table; survives occlusion / ID switches shorter than table_merge_gap_seconds."""
        for z in self.zones:
            if z.kind != "table":
                continue
            sitters = [st for st in self.tracks.values() if st.sitting and z.name in st.zones]
            sess = self.table_sessions.get(z.name)
            if sitters:
                if sess is None:
                    seated_at = min(st.still_since for st in sitters)
                    sid = self._store("open_table_session", z.name, seated_at)
                    self.table_sessions[z.name] = {"id": sid, "seated_at": seated_at, "last_occupied": t}
                else:
                    sess["last_occupied"] = t
            elif sess is not None and t - sess["last_occupied"] > self.cfg.table_merge_gap_seconds:
                self._close_table(z.name)

    def _close_table(self, name: str) -> None:
        sess = self.table_sessions.pop(name)
        if sess["id"] is not None:
            self._store("close_table_session", sess["id"], sess["last_occupied"])

    def _expire(self, t: float, force: bool = False) -> None:
        for tid, st in list(self.tracks.items()):
            if not force and t - st.last_t <= self.cfg.visit_timeout_seconds:
                continue
            for name in list(st.zones):
                self._close_zone(tid, st, name, st.last_t)
            if st.last_t - st.first_t >= self.cfg.min_visit_seconds:
                self._store("add_visit", tid, st.first_t, st.last_t, st.entry_side)
            del self.tracks[tid]

    def _store(self, method: str, *args):
        return getattr(self.storage, method)(*args) if self.storage else None

    # ----------------------------------------------------------------- heatmap
    def _add_heat(self, x: float, y: float) -> None:
        s = self.cfg.heatmap_scale
        r = min(int(y * s), self.heatmap.shape[0] - 1)
        c = min(int(x * s), self.heatmap.shape[1] - 1)
        if r >= 0 and c >= 0:
            self.heatmap[r, c] += 1

    def _sample_background(self, frame: np.ndarray, t: float) -> None:
        """Median of sparse samples removes passers-by; heavy blur on save hides faces."""
        if self._last_bg_t is not None and t - self._last_bg_t < 10:
            return
        self._last_bg_t = t
        small = cv2.resize(frame, (self.heatmap.shape[1] * 2, self.heatmap.shape[0] * 2))
        self._bg_samples = (self._bg_samples + [small])[-20:]

    def heatmap_image(self) -> np.ndarray:
        hm = cv2.GaussianBlur(self.heatmap, (0, 0), sigmaX=3)
        norm = (255 * hm / hm.max()).astype(np.uint8) if hm.max() > 0 else hm.astype(np.uint8)
        color = cv2.applyColorMap(norm, cv2.COLORMAP_JET)
        color = cv2.resize(color, (self.heatmap.shape[1] * 2, self.heatmap.shape[0] * 2))
        if not self._bg_samples:
            return color
        bg = np.median(np.stack(self._bg_samples), axis=0).astype(np.uint8)
        bg = cv2.GaussianBlur(bg, (0, 0), sigmaX=4)  # privacy: no recognisable faces on disk
        return cv2.addWeighted(bg, 0.55, color, 0.45, 0)

    def save_heatmap(self) -> None:
        out = Path(self.cfg.exports_dir)
        out.mkdir(parents=True, exist_ok=True)
        np.save(out / "heatmap.npy", self.heatmap)
        cv2.imwrite(str(out / "heatmap.png"), self.heatmap_image())

    # ---------------------------------------------------------------- lifecycle
    def finalize(self, t: float) -> None:
        """Flush open visits, zone events and table sessions (call at shutdown)."""
        self._expire(t, force=True)
        for name in list(self.table_sessions):
            self._close_table(name)
        self.save_heatmap()

    # --------------------------------------------------------------- rendering
    def draw(self, frame: np.ndarray, detections: sv.Detections) -> np.ndarray:
        for z in self.zones:
            color = ZONE_COLORS.get(z.kind, ZONE_COLORS["area"])
            occupancy = sum(1 for st in self.tracks.values() if z.name in st.zones)
            cv2.polylines(frame, [z.polygon.astype(np.int32)], True, color, 2)
            x, y = z.polygon.min(axis=0)
            cv2.putText(frame, f"{z.name}: {occupancy}", (int(x) + 4, int(y) + 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        if self.door_line is not None:
            s, e = self.door_line.vector.start, self.door_line.vector.end
            cv2.line(frame, (int(s.x), int(s.y)), (int(e.x), int(e.y)), (0, 255, 255), 2)
            cv2.putText(frame, f"IN {self.count_in}  OUT {self.count_out}", (int(s.x), int(s.y) - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        if len(detections) and detections.tracker_id is not None:
            feet = detections.get_anchors_coordinates(ANCHOR)
            for (x, y), tid in zip(feet, detections.tracker_id):
                st = self.tracks.get(int(tid))
                if st is not None and st.sitting:
                    cv2.putText(frame, "duduk", (int(x) - 20, int(y) + 16),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (80, 200, 80), 2)
        return frame
