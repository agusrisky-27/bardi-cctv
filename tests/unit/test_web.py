"""Laptop-use activity + web dashboard API (ranges, auth, read-only)."""

from __future__ import annotations

from datetime import datetime
import sqlite3

import numpy as np
import supervision as sv
from fastapi.testclient import TestClient

from rcis.analytics import RestaurantAnalytics
from rcis.config.settings import AnalyticsConfig
from rcis.storage import Storage
from rcis.web import LiveState, create_app, query_stats

NOW = datetime(2026, 11, 9, 15, 30)  # a Monday afternoon


def _person(tid: int, x: float = 500, y: float = 700) -> sv.Detections:
    return sv.Detections(xyxy=np.array([[x - 60, y - 300, x + 60, y]], dtype=float), confidence=np.array([0.9]),
                         class_id=np.array([0]), tracker_id=np.array([tid]))


def _laptop(x: float = 500, y: float = 520) -> sv.Detections:
    return sv.Detections(xyxy=np.array([[x - 50, y - 30, x + 50, y + 30]], dtype=float), confidence=np.array([0.8]),
                         class_id=np.array([63]))


def _analytics(tmp_path) -> RestaurantAnalytics:
    cfg = AnalyticsConfig(exports_dir=str(tmp_path), speed_window_seconds=1.0, visit_timeout_seconds=3,
                          heatmap_save_every_seconds=1e9, laptop_min_seconds=5, laptop_gap_seconds=3)
    return RestaurantAnalytics(cfg, (1000, 1000), [], None, Storage(":memory:"))


def test_laptop_session_tolerates_missed_detections(tmp_path):
    a = _analytics(tmp_path)
    t = 1_700_000_000.0
    for i in range(41):  # 20 s still at a laptop; the laptop is missed every 4th frame
        a.update(_person(1), t + i * 0.5, laptops=sv.Detections.empty() if i % 4 == 3 else _laptop())
    assert a.live_summary()["laptop_now"] == 1
    for i in range(1, 12):  # laptop closed / gone
        a.update(_person(1), t + 20 + i * 0.5, laptops=sv.Detections.empty())
    rows = a.storage.conn.execute("SELECT activity, seconds FROM activity_events").fetchall()
    assert len(rows) == 1 and rows[0][0] == "laptop" and 18 <= rows[0][1] <= 20


def test_laptop_far_away_or_walking_does_not_count(tmp_path):
    a = _analytics(tmp_path)
    t = 1_700_000_000.0
    for i in range(30):  # still, but the laptop is on another desk
        a.update(_person(1, x=200), t + i * 0.5, laptops=_laptop(x=800))
    for i in range(30):  # walking past a laptop
        a.update(_person(2, x=100 + i * 30), t + i * 0.5, laptops=_laptop(x=500))
    a.finalize(t + 30)
    assert a.storage.conn.execute("SELECT COUNT(*) FROM activity_events").fetchone()[0] == 0


def _seed(db) -> None:
    s = Storage(db)
    today, yesterday = datetime(2026, 11, 9, 10).timestamp(), datetime(2026, 11, 8, 10).timestamp()
    last_month = datetime(2026, 10, 1, 10).timestamp()
    s.add_visit(1, today, today + 600, "kiri", "male", 0.9)
    s.add_visit(2, today + 60, today + 120, "kanan", None, None)
    s.add_visit(3, today, today + 900, "kiri", None, None, "staff")  # excluded from visitors
    s.add_visit(4, yesterday, yesterday + 300, "depan", "female", 0.8)
    s.add_visit(5, last_month, last_month + 60, "kiri")
    s.add_activity(1, "laptop", today, today + 300)
    s.add_activity(1, "laptop", today + 400, today + 500)
    s.add_zone_event(1, "meja_1", today, today + 600, True)
    s.add_line_crossing(1, "in", "kiri", today)
    s.close()


def test_stats_ranges(tmp_path):
    db = tmp_path / "rcis.db"
    _seed(db)
    conn = Storage(db).conn
    today = query_stats(conn, "today", NOW)
    assert today["visitors"] == 2 and today["gender"] == {"male": 1, "female": 0, "unknown": 1}
    assert today["entry_sides"] == {"kiri": 1, "kanan": 1}
    assert today["series"]["values"][10] == 2 and len(today["series"]["labels"]) == 24
    assert today["laptop"]["total_seconds"] == 400 and today["laptop"]["per_person"][0]["sessions"] == 2
    assert today["zones"][0]["zone"] == "meja_1" and today["door"] == {"in": 1}
    assert query_stats(conn, "yesterday", NOW)["visitors"] == 1
    week = query_stats(conn, "7d", NOW)
    assert week["visitors"] == 3 and len(week["series"]["labels"]) == 7 and week["series"]["values"][-1] == 2
    assert query_stats(conn, "30d", NOW)["visitors"] == 3  # 1 Oct is outside the last 30 days


def test_api_auth_and_live(tmp_path):
    db = tmp_path / "rcis.db"
    _seed(db)
    live = LiveState()
    live.set(b"\xff\xd8jpeg", {"people_now": 2})
    client = TestClient(create_app(db, live, tmp_path, password="rahasia"))
    assert client.get("/api/stats").status_code == 401
    assert client.get("/api/stats", auth=("x", "salah")).status_code == 401
    r = client.get("/api/stats?range=7d", auth=("x", "rahasia"))
    assert r.status_code == 200 and r.json()["range"] == "7d"
    assert client.get("/api/stats?range=999d", auth=("x", "rahasia")).status_code == 422
    assert client.get("/api/live", auth=("x", "rahasia")).json() == {"available": True, "people_now": 2}
    assert "CCTV Analitik" in client.get("/", auth=("x", "rahasia")).text


def test_api_without_password_and_without_pipeline(tmp_path):
    client = TestClient(create_app(tmp_path / "missing.db", None, tmp_path))
    assert client.get("/api/stats").status_code == 404  # DB not created yet
    assert client.get("/api/live").json() == {"available": False}
    assert client.get("/video").status_code == 404


def test_backup_copies_all_rows(tmp_path):
    db = tmp_path / "rcis.db"
    _seed(db)
    s = Storage(db)
    daily = s.backup(tmp_path / "backup")
    s.add_visit(9, 0, 1, "kiri")  # written after the backup: must not appear in it
    for f in (daily, tmp_path / "backup" / "rcis_latest.db"):
        assert sqlite3.connect(f).execute("SELECT COUNT(*) FROM visits").fetchone()[0] == 5


def test_backup_keeps_only_recent_days(tmp_path):
    dest = tmp_path / "backup"
    dest.mkdir()
    for day in range(1, 21):  # 20 old daily backups
        (dest / f"rcis_2026-10-{day:02d}.db").write_bytes(b"x")
    Storage(":memory:").backup(dest, keep_days=14)
    dailies = sorted(dest.glob("rcis_????-??-??.db"))
    assert len(dailies) == 14 and dailies[-1].name.startswith("rcis_2026-11")  # today's kept, oldest gone
    assert (dest / "rcis_latest.db").exists()


def test_live_count_ignores_people_who_just_left(tmp_path):
    a = _analytics(tmp_path)  # visit_timeout_seconds=3
    t = 1_700_000_000.0
    for i in range(4):
        a.update(_person(1), t + i * 0.5)
    a.update(sv.Detections.empty(), t + 3.0)  # #1 walked out 1.5 s ago: still kept for the visit log
    a.update(_person(2, x=300), t + 3.5)  # walks straight back in as a new track
    assert 1 in a.tracks and a.live_summary()["people_now"] == 1
