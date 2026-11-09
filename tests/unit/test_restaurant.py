"""Tests for gender voting, food-wait timing, staff detection and the DB role migration."""

from __future__ import annotations


import numpy as np
import supervision as sv

from rcis.analytics import RestaurantAnalytics, load_zones
from rcis.config.settings import AnalyticsConfig
from rcis.gender import aggregate_votes
from memdb import memory_storage

W, H = 1000, 1000
NAMES = ["female", "male"]


def _det(tid: int, x: float, y: float) -> sv.Detections:
    return sv.Detections(
        xyxy=np.array([[x - 40, y - 200, x + 40, y]], dtype=float),
        confidence=np.array([0.9]), class_id=np.array([0]), tracker_id=np.array([tid]),
    )


def _box(cx: float, cy: float, half: float = 30) -> sv.Detections:
    return sv.Detections(xyxy=np.array([[cx - half, cy - half, cx + half, cy + half]], dtype=float),
                         confidence=np.array([0.9]), class_id=np.array([0]))


def _make(tmp_path, zones_extra: str = "") -> RestaurantAnalytics:
    y = tmp_path / "zones.yaml"
    y.write_text(
        "coordinate_format: normalized\nzones:\n"
        "  - {name: meja_1, kind: table, polygon: [[0.5, 0.5], [0.9, 0.5], [0.9, 0.9], [0.5, 0.9]]}\n"
        "  - {name: meja_2, kind: table, polygon: [[0.0, 0.5], [0.4, 0.5], [0.4, 0.9], [0.0, 0.9]]}\n" + zones_extra
    )
    cfg = AnalyticsConfig(exports_dir=str(tmp_path), sitting_min_seconds=5, speed_window_seconds=1.0,
                          visit_timeout_seconds=3, table_merge_gap_seconds=4, heatmap_save_every_seconds=1e9,
                          food_confirm_seconds=2, staff_min_tables=2)
    zones, line = load_zones(y, W, H)
    return RestaurantAnalytics(cfg, (W, H), zones, line, memory_storage())


def _sit(a: RestaurantAnalytics, t0: float, seconds: float = 8) -> float:
    for i in range(int(seconds * 2) + 1):
        a.update(_det(1, 700, 700), t0 + i * 0.5)
    return t0 + seconds


def _wait(a: RestaurantAnalytics):
    return a.storage.conn.execute("SELECT wait_seconds FROM table_sessions").fetchone()[0]


def test_gender_votes():
    male, female, unsure = np.array([0.1, 0.9]), np.array([0.9, 0.1]), np.array([0.55, 0.45])
    assert aggregate_votes([male] * 4, NAMES, 5, 0.65) == (None, None)  # too few votes
    assert aggregate_votes([male] * 5, NAMES, 5, 0.65) == ("male", 0.9)
    assert aggregate_votes([male, male, male, female, female, female], NAMES, 5, 0.65)[0] is None  # split vote
    assert aggregate_votes([unsure] * 6, NAMES, 5, 0.65)[0] is None  # low confidence -> unknown


def test_food_arrival_sets_wait_seconds(tmp_path):
    a = _make(tmp_path)
    t = _sit(a, 1_700_000_000.0)
    assert a.table_sessions["meja_1"]["id"] is not None
    a.update(_det(1, 700, 700), t + 0.5, food=sv.Detections.empty())  # a round with no plate yet
    for i in range(1, 8):  # plate appears on the table and stays
        a.update(_det(1, 700, 700), t + i, food=_box(700, 650))
    assert 5 <= _wait(a) <= 15  # arrival ~2 s after the plate appeared, well after seating


def test_plate_already_on_table_does_not_count(tmp_path):
    a = _make(tmp_path)
    t0 = 1_700_000_000.0
    for i in range(17):  # sits 8 s with a plate already there
        a.update(_det(1, 700, 700), t0 + i * 0.5, food=_box(700, 650))
    assert _wait(a) is None
    a.update(_det(1, 700, 700), t0 + 9, food=sv.Detections.empty())  # plate cleared
    for i in range(6):  # a new plate arrives
        a.update(_det(1, 700, 700), t0 + 10 + i, food=_box(700, 650))
    assert _wait(a) is not None


def test_waiter_overlap_marks_staff_and_skips_table_session(tmp_path):
    a = _make(tmp_path)
    t = 1_700_000_000.0
    for i in range(21):
        det = _det(1, 700, 700)
        a.update(det, t + i * 0.5, waiters=sv.Detections(xyxy=det.xyxy.copy(), confidence=np.array([0.9]),
                                                         class_id=np.array([0])))
    assert a.tracks[1].is_staff and not a.tracks[1].sitting
    assert not a.table_sessions
    a.update(sv.Detections.empty(), t + 30)
    row = a.storage.conn.execute("SELECT role, gender_est FROM visits").fetchone()
    assert row == ("staff", None)
    assert a.storage.conn.execute("SELECT COUNT(*) FROM visits WHERE role = 'customer'").fetchone()[0] == 0


def test_walking_between_tables_marks_staff(tmp_path):
    a = _make(tmp_path)
    t = 1_700_000_000.0
    for i, x in enumerate([700, 700, 200, 200]):  # meja_1 then meja_2 (staff_min_tables=2)
        a.update(_det(1, x, 700), t + i)
    assert a.tracks[1].is_staff


def test_gender_goes_to_visit_for_customers(tmp_path):
    a = _make(tmp_path)
    a.gender_lookup = lambda tid: ("female", 0.91)
    t = 1_700_000_000.0
    for i in range(10):
        a.update(_det(1, 700, 700), t + i * 0.5)
    a.update(sv.Detections.empty(), t + 20)
    assert a.storage.conn.execute("SELECT role, gender_est, gender_conf FROM visits").fetchone() == ("customer", "female", 0.91)


def test_office_mode_never_marks_desk_hoppers_as_staff(tmp_path):
    a = _make(tmp_path)
    a.cfg.staff_min_tables = 0  # office: walking between desks is normal
    t = 1_700_000_000.0
    for i, x in enumerate([700, 700, 200, 200, 700, 700]):
        a.update(_det(1, x, 700), t + i)
    assert not a.tracks[1].is_staff

def test_id_switch_is_relinked_into_one_visit(tmp_path):
    a = _make(tmp_path)
    a.gender_lookup = lambda tid: ("male", 0.8) if tid == 1 else (None, None)
    t = 1_700_000_000.0
    for i in range(10):
        a.update(_det(1, 700, 700), t + i * 0.5)
    for i in range(10):  # tracker lost ID 1 and gave the same person ID 2, a few pixels away
        a.update(_det(2, 710, 705), t + 6 + i * 0.5)
    a.update(sv.Detections.empty(), t + 30)
    rows = a.storage.conn.execute("SELECT entered_at, exited_at, gender_est FROM visits").fetchall()
    assert len(rows) == 1 and rows[0][2] == "male"


def test_far_new_id_is_a_new_person(tmp_path):
    a = _make(tmp_path)
    t = 1_700_000_000.0
    for i in range(6):
        a.update(_det(1, 700, 700), t + i * 0.5)
    for i in range(6):
        a.update(_det(2, 100, 300), t + 3 + i * 0.5)
    a.update(sv.Detections.empty(), t + 30)
    assert a.storage.conn.execute("SELECT COUNT(*) FROM visits").fetchone()[0] == 2
