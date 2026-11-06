"""Synthetic-track tests for door line, zones, sitting, table sessions and visit storage."""

from __future__ import annotations

import numpy as np
import supervision as sv

from rcis.analytics import RestaurantAnalytics, load_zones
from rcis.config.settings import AnalyticsConfig
from rcis.storage import Storage

W, H = 1000, 1000


def _det(tid: int, foot_x: float, foot_y: float) -> sv.Detections:
    """One person box whose bottom-center footpoint is (foot_x, foot_y)."""
    return sv.Detections(
        xyxy=np.array([[foot_x - 40, foot_y - 200, foot_x + 40, foot_y]], dtype=float),
        confidence=np.array([0.9]),
        class_id=np.array([0]),
        tracker_id=np.array([tid]),
    )


def _make(tmp_path) -> RestaurantAnalytics:
    zones_yaml = tmp_path / "zones.yaml"
    zones_yaml.write_text(
        "coordinate_format: normalized\n"
        "door_line: {start: [0.0, 0.5], end: [0.2, 0.5]}\n"
        "zones:\n"
        "  - {name: meja_1, kind: table, polygon: [[0.5, 0.5], [0.9, 0.5], [0.9, 0.9], [0.5, 0.9]]}\n"
    )
    cfg = AnalyticsConfig(
        exports_dir=str(tmp_path), sitting_min_seconds=5, speed_window_seconds=1.0,
        visit_timeout_seconds=3, table_merge_gap_seconds=4, heatmap_save_every_seconds=1e9,
    )
    zones, line = load_zones(zones_yaml, W, H)
    return RestaurantAnalytics(cfg, (W, H), zones, line, Storage(":memory:"))


def test_walk_in_sit_and_leave(tmp_path):
    a = _make(tmp_path)
    t = 1_700_000_000.0
    # enters from the left edge, walks down through the door line
    for i, y in enumerate([400, 450, 480, 520, 560, 600]):
        a.update(_det(1, 100, y), t + i * 0.5)
    t += 3.0
    # walks to the table and sits still for 10 s (sampled at 2 FPS)
    for i in range(21):
        a.update(_det(1, 700, 700), t + i * 0.5)
    assert a.tracks[1].sitting
    assert "meja_1" in a.table_sessions
    t += 10.5
    # disappears: visit closes after timeout, table session after merge gap
    a.update(sv.Detections.empty(), t + 10)

    db = a.storage.conn
    assert a.count_in + a.count_out == 1
    assert db.execute("SELECT entry_side FROM line_crossings").fetchone()[0] == "kiri"
    visit = db.execute("SELECT entry_side, total_seconds FROM visits").fetchone()
    assert visit[0] == "kiri" and visit[1] > 10
    zone = db.execute("SELECT zone_name, is_sitting, seconds FROM zone_events").fetchone()
    assert zone[0] == "meja_1" and zone[1] == 1 and zone[2] >= 10
    session = db.execute("SELECT seated_at, left_at FROM table_sessions").fetchone()
    assert session[0] is not None and session[1] is not None
    assert db.execute("SELECT visitors FROM hourly_stats").fetchone()[0] == 1
    assert a.heatmap.sum() == 27


def test_id_switch_keeps_one_table_session(tmp_path):
    a = _make(tmp_path)
    t = 0.0
    for i in range(13):  # track 1 sits 6 s
        a.update(_det(1, 700, 700), t + i * 0.5)
    t += 7
    for i in range(13):  # occluded, re-detected as track 2 within the merge gap
        a.update(_det(2, 705, 700), t + i * 0.5)
    a.finalize(t + 7)
    assert a.storage.conn.execute("SELECT COUNT(*) FROM table_sessions").fetchone()[0] == 1


def test_food_wait_seconds(tmp_path):
    s = Storage(":memory:")
    sid = s.open_table_session("meja_1", 1_700_000_000.0)
    s.set_food_arrived(sid, 1_700_000_090.0)
    s.set_food_arrived(sid, 1_700_000_500.0)  # later plates do not overwrite the first arrival
    assert s.conn.execute("SELECT wait_seconds FROM table_sessions").fetchone()[0] == 90.0
