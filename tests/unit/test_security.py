"""Security alerts: rules, cooldowns, face blur, snapshot endpoint."""

from __future__ import annotations

from pathlib import Path

from datetime import datetime

import numpy as np
import supervision as sv
from fastapi.testclient import TestClient

from rcis.analytics import RestaurantAnalytics, load_zones
from rcis.config.settings import AnalyticsConfig, SecurityConfig
from rcis.security import Security, blur_faces
from memdb import memory_storage
from rcis.web import create_app

W = H = 1000


def _det(tid: int, x: float, y: float) -> sv.Detections:
    return sv.Detections(xyxy=np.array([[x - 40, y - 200, x + 40, y]], dtype=float), confidence=np.array([0.9]),
                         class_id=np.array([0]), tracker_id=np.array([tid]))


def _setup(tmp_path, **sec):
    zones_yaml = tmp_path / "z.yaml"
    zones_yaml.write_text("coordinate_format: normalized\nzones:\n"
                          "  - {name: gudang, kind: restricted, polygon: [[0.5, 0.5], [0.9, 0.5], [0.9, 0.9], [0.5, 0.9]]}\n"
                          "  - {name: meja, kind: table, polygon: [[0.0, 0.5], [0.4, 0.5], [0.4, 0.9], [0.0, 0.9]]}\n")
    storage = memory_storage()
    zones, line = load_zones(zones_yaml, W, H)
    analytics = RestaurantAnalytics(AnalyticsConfig(exports_dir=str(tmp_path), heatmap_save_every_seconds=1e9,
                                                    sitting_min_seconds=5, speed_window_seconds=1.0),
                                    (W, H), zones, line, storage)
    sent = []
    security = Security(SecurityConfig(alerts_dir=str(tmp_path / "alerts"), **sec), storage,
                        sender=lambda caption, jpeg: sent.append((caption, jpeg)))
    return analytics, security, storage, sent


def _step(analytics, security, det, t, frame=None):
    analytics.update(det, t)
    security.check(frame if frame is not None else np.full((H, W, 3), 90, np.uint8), det, analytics, t)


def test_blur_hides_head_but_not_body():
    rng = np.random.default_rng(0)
    frame = rng.integers(0, 255, (400, 400, 3), dtype=np.uint8)
    out = blur_faces(frame, np.array([[100, 50, 200, 350]], dtype=float), head_fraction=0.25)
    head, body = (slice(55, 120), slice(110, 190)), (slice(200, 340), slice(110, 190))
    assert out[head].std() < frame[head].std() / 3  # head region is smooth now
    assert np.array_equal(out[body], frame[body])  # body untouched
    assert not np.array_equal(out, frame) and frame is not out


def test_restricted_zone_alert_with_cooldown_and_snapshot(tmp_path):
    a, sec, storage, sent = _setup(tmp_path, restricted_cooldown_seconds=60)
    t = 1_700_000_000.0
    for i in range(5):  # stays in the restricted zone for 2 s
        _step(a, sec, _det(1, 700, 700), t + i * 0.5)
    assert len(sent) == 1 and "gudang" in sent[0][0] and sent[0][1][:2] == b"\xff\xd8"  # one Telegram photo
    _step(a, sec, _det(1, 700, 700), t + 61)  # after cooldown -> second alert
    assert len(storage.conn.execute("SELECT * FROM alerts").fetchall()) == 2
    file = storage.conn.execute("SELECT snapshot_path_blurred FROM alerts").fetchone()[0]
    assert file.endswith(".jpg") and (tmp_path / "alerts").exists()


def test_no_alert_outside_restricted_zone(tmp_path):
    a, sec, storage, sent = _setup(tmp_path)
    for i in range(10):
        _step(a, sec, _det(1, 200, 700), 1_700_000_000.0 + i)  # inside the table zone only
    assert not sent and storage.conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 0


def test_loitering_once_per_person_but_not_when_sitting(tmp_path):
    a, sec, storage, sent = _setup(tmp_path, loiter_seconds=20)
    t = 1_700_000_000.0
    for i in range(0, 60, 2):  # person 1 keeps walking around the middle for 60 s
        _step(a, sec, _det(1, 450 + (i % 4) * 50, 300 + (i % 6) * 20), t + i)
    kinds = [r[0] for r in storage.conn.execute("SELECT type FROM alerts")]
    assert kinds == ["loitering"]  # once, not every frame
    for i in range(0, 60, 1):  # person 2 sits still at a table for 60 s
        _step(a, sec, _det(2, 200, 700), t + 100 + i)
    assert [r[0] for r in storage.conn.execute("SELECT type FROM alerts")] == ["loitering"]


def test_after_hours(tmp_path):
    a, sec, storage, sent = _setup(tmp_path, open_hour=8, close_hour=22)
    noon, night = datetime(2026, 11, 9, 12).timestamp(), datetime(2026, 11, 9, 23).timestamp()
    _step(a, sec, _det(1, 200, 700), noon)
    assert storage.conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 0
    _step(a, sec, _det(1, 200, 700), night)
    assert storage.conn.execute("SELECT type FROM alerts").fetchone()[0] == "after_hours"
    assert Security(SecurityConfig(open_hour=None, close_hour=None), sender=None)._after_hours(night) is False
    overnight = Security(SecurityConfig(open_hour=20, close_hour=4), sender=None)  # open 20:00-04:00
    assert overnight._after_hours(noon) and not overnight._after_hours(night)


def test_telegram_failure_does_not_leak_token_or_crash(tmp_path, caplog):
    import requests

    def boom(caption, jpeg):
        raise requests.ConnectionError("https://api.telegram.org/botSECRET123/sendPhoto failed")

    a, sec, storage, _ = _setup(tmp_path)
    sec.sender = boom
    sec._send("x", b"y")
    assert "SECRET123" not in caplog.text and "ConnectionError" in caplog.text


def test_alert_row_and_snapshot_endpoint(tmp_path):
    a, sec, storage, sent = _setup(tmp_path)
    now = datetime.now().timestamp()
    for i in range(3):
        _step(a, sec, _det(1, 700, 700), now + i * 0.5)
    kind, snapshot = storage.conn.execute("SELECT type, snapshot_path_blurred FROM alerts").fetchone()
    name = Path(snapshot).name
    assert kind == "restricted_zone" and name.endswith(".jpg")
    client = TestClient(create_app(None, tmp_path, alerts_dir=tmp_path / "alerts"))
    assert client.get(f"/alert-snapshot/{name}").status_code == 200
    assert client.get("/alert-snapshot/..%2Fweb.db").status_code == 404
    assert client.get("/alert-snapshot/missing.jpg").status_code == 404


def test_loitering_off_when_zero(tmp_path):
    a, sec, storage, sent = _setup(tmp_path, loiter_seconds=0)
    t = 1_700_000_000.0
    for i in range(0, 60, 2):
        _step(a, sec, _det(1, 450 + (i % 4) * 50, 300 + (i % 6) * 20), t + i)
    assert storage.conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0] == 0
