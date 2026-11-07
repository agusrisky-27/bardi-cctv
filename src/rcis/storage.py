"""
SQLite storage for anonymous, aggregated analytics.

Privacy: only temporary track IDs, timestamps, zone names, durations and the
voted gender label are stored. No images, crops, embeddings or identities.
"""

from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path
import shutil
import sqlite3
from typing import Optional

logger = logging.getLogger("rcis.storage")

# shortcut: stdlib sqlite3 instead of SQLAlchemy (no extra dependency); switch if a server DB is needed.
SCHEMA = """
CREATE TABLE IF NOT EXISTS visits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER NOT NULL,
    entered_at TEXT NOT NULL,
    exited_at TEXT,
    entry_side TEXT,
    gender_est TEXT,
    gender_conf REAL,
    total_seconds REAL,
    role TEXT NOT NULL DEFAULT 'customer'  -- customer / staff (waiter)
);
CREATE TABLE IF NOT EXISTS zone_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER NOT NULL,
    zone_name TEXT NOT NULL,
    enter_at TEXT NOT NULL,
    exit_at TEXT,
    seconds REAL,
    is_sitting INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS table_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_zone TEXT NOT NULL,
    seated_at TEXT NOT NULL,
    food_arrived_at TEXT,
    wait_seconds REAL,
    left_at TEXT
);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    zone_name TEXT,
    created_at TEXT NOT NULL,
    snapshot_path_blurred TEXT
);
CREATE TABLE IF NOT EXISTS line_crossings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER NOT NULL,
    direction TEXT NOT NULL,          -- 'in' / 'out'
    entry_side TEXT,                  -- kiri / kanan / depan (asal lintasan)
    crossed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS activity_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER NOT NULL,
    activity TEXT NOT NULL,           -- e.g. 'laptop' (sitting in front of a laptop)
    start_at TEXT NOT NULL,
    end_at TEXT NOT NULL,
    seconds REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_visits_entered ON visits(entered_at);
CREATE INDEX IF NOT EXISTS idx_activity_start ON activity_events(start_at);
CREATE INDEX IF NOT EXISTS idx_zone_events_zone ON zone_events(zone_name);

"""


VIEW = """
-- hourly_stats is a view so it never drifts from the raw anonymous rows.
DROP VIEW IF EXISTS hourly_stats;
CREATE VIEW hourly_stats AS
SELECT v.hour,
       v.visitors, v.male, v.female, v.unknown, v.avg_dwell,
       f.avg_food_wait
FROM (
    SELECT strftime('%Y-%m-%d %H:00', entered_at) AS hour,
           COUNT(*) AS visitors,
           IFNULL(SUM(gender_est = 'male'), 0) AS male,
           IFNULL(SUM(gender_est = 'female'), 0) AS female,
           SUM(gender_est IS NULL OR gender_est NOT IN ('male', 'female')) AS unknown,
           AVG(total_seconds) AS avg_dwell
    FROM visits WHERE role = 'customer' GROUP BY hour
) v
LEFT JOIN (
    SELECT strftime('%Y-%m-%d %H:00', seated_at) AS hour, AVG(wait_seconds) AS avg_food_wait
    FROM table_sessions WHERE wait_seconds IS NOT NULL GROUP BY hour
) f ON f.hour = v.hour;
"""


def _iso(ts: Optional[float]) -> Optional[str]:
    return None if ts is None else datetime.fromtimestamp(ts).isoformat(timespec="seconds")


class Storage:
    """Thin writer over SQLite. All timestamps are epoch seconds, stored as local ISO strings."""

    def __init__(self, db_path: str | Path) -> None:
        path = Path(db_path)
        if str(db_path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")  # dashboard can read while the pipeline writes
        self.conn.executescript(SCHEMA)
        cols = {row[1] for row in self.conn.execute("PRAGMA table_info(visits)")}
        if "role" not in cols:  # DB created before the role column existed
            self.conn.execute("ALTER TABLE visits ADD COLUMN role TEXT NOT NULL DEFAULT 'customer'")
        self.conn.executescript(VIEW)
        self.conn.commit()

    def _insert(self, sql: str, params: tuple) -> int:
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return int(cur.lastrowid)

    def add_visit(
        self,
        track_id: int,
        entered_at: float,
        exited_at: float,
        entry_side: Optional[str],
        gender_est: Optional[str] = None,
        gender_conf: Optional[float] = None,
        role: str = "customer",
    ) -> int:
        return self._insert(
            "INSERT INTO visits (track_id, entered_at, exited_at, entry_side, gender_est, gender_conf, total_seconds, role)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (track_id, _iso(entered_at), _iso(exited_at), entry_side, gender_est, gender_conf,
             round(exited_at - entered_at, 2), role),
        )

    def add_zone_event(self, track_id: int, zone_name: str, enter_at: float, exit_at: float, is_sitting: bool) -> int:
        return self._insert(
            "INSERT INTO zone_events (track_id, zone_name, enter_at, exit_at, seconds, is_sitting) VALUES (?, ?, ?, ?, ?, ?)",
            (track_id, zone_name, _iso(enter_at), _iso(exit_at), round(exit_at - enter_at, 2), int(is_sitting)),
        )

    def add_line_crossing(self, track_id: int, direction: str, entry_side: Optional[str], crossed_at: float) -> int:
        return self._insert(
            "INSERT INTO line_crossings (track_id, direction, entry_side, crossed_at) VALUES (?, ?, ?, ?)",
            (track_id, direction, entry_side, _iso(crossed_at)),
        )

    def add_activity(self, track_id: int, activity: str, start_at: float, end_at: float) -> int:
        return self._insert(
            "INSERT INTO activity_events (track_id, activity, start_at, end_at, seconds) VALUES (?, ?, ?, ?, ?)",
            (track_id, activity, _iso(start_at), _iso(end_at), round(end_at - start_at, 2)),
        )

    def add_alert(self, alert_type: str, zone_name: Optional[str], created_at: float, snapshot: Optional[str]) -> int:
        return self._insert(
            "INSERT INTO alerts (type, zone_name, created_at, snapshot_path_blurred) VALUES (?, ?, ?, ?)",
            (alert_type, zone_name, _iso(created_at), snapshot),
        )

    def open_table_session(self, table_zone: str, seated_at: float) -> int:
        return self._insert(
            "INSERT INTO table_sessions (table_zone, seated_at) VALUES (?, ?)", (table_zone, _iso(seated_at))
        )

    def close_table_session(self, session_id: int, left_at: float) -> None:
        self.conn.execute("UPDATE table_sessions SET left_at = ? WHERE id = ?", (_iso(left_at), session_id))
        self.conn.commit()

    def set_food_arrived(self, session_id: int, arrived_at: float) -> None:
        """Used by the food detector (Phase 3) or manual/POS input. Only the first arrival counts."""
        self.conn.execute(
            "UPDATE table_sessions SET food_arrived_at = ?,"
            " wait_seconds = ROUND((julianday(?) - julianday(seated_at)) * 86400, 2)"
            " WHERE id = ? AND food_arrived_at IS NULL",
            (_iso(arrived_at), _iso(arrived_at), session_id),
        )
        self.conn.commit()

    def backup(self, dest_dir: str | Path, keep_days: int = 14) -> Path:
        """Consistent online copy (safe while writing): one file per day + rcis_latest.db; older dailies deleted."""
        dest = Path(dest_dir).expanduser()
        dest.mkdir(parents=True, exist_ok=True)
        daily = dest / f"rcis_{datetime.now():%Y-%m-%d}.db"
        out = sqlite3.connect(str(daily))
        try:
            self.conn.backup(out)
        finally:
            out.close()
        shutil.copy2(daily, dest / "rcis_latest.db")
        for old in sorted(dest.glob("rcis_????-??-??.db"))[:-keep_days]:  # names sort by date
            old.unlink()
        return daily

    def close(self) -> None:
        self.conn.close()
