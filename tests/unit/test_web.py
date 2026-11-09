"""Laptop-use activity + web dashboard API (ranges, auth, read-only)."""

from __future__ import annotations


import numpy as np
import supervision as sv
from fastapi.testclient import TestClient

from rcis.analytics import RestaurantAnalytics
from rcis.config.settings import AnalyticsConfig
from memdb import memory_storage
from rcis.web import LiveState, create_app



def _person(tid: int, x: float = 500, y: float = 700) -> sv.Detections:
    return sv.Detections(xyxy=np.array([[x - 60, y - 300, x + 60, y]], dtype=float), confidence=np.array([0.9]),
                         class_id=np.array([0]), tracker_id=np.array([tid]))


def _laptop(x: float = 500, y: float = 520) -> sv.Detections:
    return sv.Detections(xyxy=np.array([[x - 50, y - 30, x + 50, y + 30]], dtype=float), confidence=np.array([0.8]),
                         class_id=np.array([63]))


def _analytics(tmp_path) -> RestaurantAnalytics:
    cfg = AnalyticsConfig(exports_dir=str(tmp_path), speed_window_seconds=1.0, visit_timeout_seconds=3,
                          heatmap_save_every_seconds=1e9, laptop_min_seconds=5, laptop_gap_seconds=3)
    return RestaurantAnalytics(cfg, (1000, 1000), [], None, memory_storage())


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


def test_video_server_auth(tmp_path):
    live = LiveState()
    live.set(b"\xff\xd8jpeg", {"people_now": 2})
    (tmp_path / "heatmap.png").write_bytes(b"png")
    client = TestClient(create_app(live, tmp_path, password="rahasia", alerts_dir=tmp_path))
    assert client.get("/heatmap.png").status_code == 401
    assert client.get("/heatmap.png", auth=("x", "salah")).status_code == 401
    assert client.get("/heatmap.png", auth=("x", "rahasia")).content == b"png"
    assert client.get("/alert-snapshot/..%2Frcis.db", auth=("x", "rahasia")).status_code == 404


def test_video_server_without_pipeline(tmp_path):
    client = TestClient(create_app(None, tmp_path))
    assert client.get("/video").status_code == 404
    assert client.get("/heatmap.png").status_code == 404


def test_backup_runs_mysqldump_and_keeps_14_days(tmp_path, monkeypatch):
    dest = tmp_path / "backup"
    dest.mkdir()
    for day in range(1, 21):  # 20 old daily backups
        (dest / f"rcis_2026-10-{day:02d}.sql").write_text("old")
    calls = []

    def fake_run(cmd, stdout, env, **kw):
        calls.append((cmd, env.get("MYSQL_PWD")))
        stdout.write(b"INSERT INTO visits VALUES (1);")

    monkeypatch.setattr("rcis.storage.subprocess.run", fake_run)
    s = memory_storage()
    s._settings = {"host": "127.0.0.1", "port": 3306, "user": "u", "password": "rahasia", "database": "rcis"}
    daily = s.backup(dest, keep_days=14)
    cmd, pwd = calls[0]
    assert "rahasia" not in cmd and pwd == "rahasia"  # password via env, never visible in `ps`
    assert "users" not in cmd and "visits" in cmd  # analytics only, no account hashes in backups
    assert daily.read_bytes().startswith(b"INSERT") and (dest / "rcis_latest.sql").exists()
    dailies = sorted(dest.glob("rcis_????-??-??.sql"))
    assert len(dailies) == 14 and dailies[-1] == daily


def test_rows_wait_in_memory_while_mysql_is_down(tmp_path):
    s = memory_storage()
    real = s.conn

    class Down:
        def cursor(self):
            raise ConnectionError("mysql off")

        def close(self):
            pass

    s.conn = Down()
    assert s.add_visit(1, 0, 60, "kiri") is None  # kept, not lost
    s._connect, s._retry_at = (lambda: real), 0.0
    s.add_visit(2, 0, 60, "kanan")
    assert real.execute("SELECT COUNT(*) FROM visits").fetchone()[0] == 2


def test_live_count_ignores_people_who_just_left(tmp_path):
    a = _analytics(tmp_path)  # visit_timeout_seconds=3
    t = 1_700_000_000.0
    for i in range(4):
        a.update(_person(1), t + i * 0.5)
    a.update(sv.Detections.empty(), t + 3.0)  # #1 walked out 1.5 s ago: still kept for the visit log
    a.update(_person(2, x=100), t + 3.5)  # someone else walks in far away: a new track, not a relink
    assert 1 in a.tracks and a.live_summary()["people_now"] == 1
