"""In-memory stand-in for the MySQL `rcis` database, so tests never touch the real one.

Same tables/columns as dashboard/database/rcis.sql (Laravel migration 2026_11_09_000000_create_rcis_tables).
"""

from __future__ import annotations

import sqlite3

from rcis.storage import Storage

SCHEMA = """
CREATE TABLE visits (id INTEGER PRIMARY KEY AUTOINCREMENT, track_id INTEGER NOT NULL, entered_at TEXT NOT NULL,
    exited_at TEXT, entry_side TEXT, gender_est TEXT, gender_conf REAL, total_seconds REAL, role TEXT NOT NULL DEFAULT 'customer');
CREATE TABLE zone_events (id INTEGER PRIMARY KEY AUTOINCREMENT, track_id INTEGER NOT NULL, zone_name TEXT NOT NULL,
    enter_at TEXT NOT NULL, exit_at TEXT, seconds REAL, is_sitting INTEGER NOT NULL DEFAULT 0);
CREATE TABLE table_sessions (id INTEGER PRIMARY KEY AUTOINCREMENT, table_zone TEXT NOT NULL, seated_at TEXT NOT NULL,
    food_arrived_at TEXT, wait_seconds REAL, left_at TEXT);
CREATE TABLE alerts (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL, zone_name TEXT, created_at TEXT NOT NULL,
    snapshot_path_blurred TEXT);
CREATE TABLE line_crossings (id INTEGER PRIMARY KEY AUTOINCREMENT, track_id INTEGER NOT NULL, direction TEXT NOT NULL,
    entry_side TEXT, crossed_at TEXT NOT NULL);
CREATE TABLE activity_events (id INTEGER PRIMARY KEY AUTOINCREMENT, track_id INTEGER NOT NULL, activity TEXT NOT NULL,
    start_at TEXT NOT NULL, end_at TEXT NOT NULL, seconds REAL NOT NULL);
CREATE TABLE live_status (id INTEGER PRIMARY KEY, people_now INTEGER, laptop_now INTEGER, count_in INTEGER,
    count_out INTEGER, fps REAL, updated_at TEXT NOT NULL);
"""


def memory_storage() -> Storage:
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.executescript(SCHEMA)
    return Storage(lambda: conn, placeholder="?")
