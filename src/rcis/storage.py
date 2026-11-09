"""
MySQL storage for anonymous, aggregated analytics (database `rcis`, shared with the Laravel dashboard).

The tables are created by dashboard/database/rcis.sql (phpMyAdmin import) or `php artisan migrate`.
Privacy: only temporary track IDs, timestamps, zone names, durations and the voted gender label are
stored. No images, crops, embeddings or identities.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
import logging
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any, Callable, Optional

logger = logging.getLogger("rcis.storage")

ANALYTICS_TABLES = ("visits", "zone_events", "table_sessions", "alerts", "line_crossings", "activity_events", "live_status")
RETRY_SECONDS = 30  # after MySQL drops out, so a dead server does not stall every frame with connect timeouts
PENDING_MAX = 50_000  # rows kept in memory while MySQL is down (~hours of office traffic)
XAMPP_MYSQLDUMP = "/Applications/XAMPP/xamppfiles/bin/mysqldump"


def _dt(ts: Optional[float]) -> Optional[str]:
    return None if ts is None else datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def mysql_settings() -> dict:
    """Connection settings from .env (RCIS_MYSQL_HOST / _PORT / _USER / _PASSWORD / _DATABASE)."""
    return dict(
        host=os.environ.get("RCIS_MYSQL_HOST") or "127.0.0.1",
        port=int(os.environ.get("RCIS_MYSQL_PORT") or 3306),
        user=os.environ.get("RCIS_MYSQL_USER") or "root",
        password=os.environ.get("RCIS_MYSQL_PASSWORD") or "",
        database=os.environ.get("RCIS_MYSQL_DATABASE") or "rcis",
    )


class Storage:
    """Writes analytics rows. If MySQL drops out mid-run, rows wait in memory and are sent when it is back."""

    def __init__(self, connect: Callable[[], Any], placeholder: str = "%s", settings: Optional[dict] = None) -> None:
        self._connect = connect
        self._placeholder = placeholder  # "%s" for PyMySQL; tests pass "?" with an in-memory stand-in
        self._settings = settings or {}
        self._pending: deque = deque(maxlen=PENDING_MAX)
        self._retry_at = 0.0
        self.conn = connect()  # fail fast: the pipeline must not start while MySQL is off

    @classmethod
    def from_env(cls) -> "Storage":
        import pymysql

        settings = mysql_settings()
        try:
            return cls(lambda: pymysql.connect(**settings, charset="utf8mb4", connect_timeout=3), settings=settings)
        except pymysql.MySQLError as e:
            raise SystemExit(
                f"MySQL tidak bisa dihubungi di {settings['host']}:{settings['port']} ({e}). "
                "Nyalakan MySQL di XAMPP dan cek RCIS_MYSQL_* di .env."
            ) from None

    # ------------------------------------------------------------------ writing
    def _write(self, sql: str, params: tuple) -> Optional[int]:
        """Queue one statement and send everything waiting. Returns the new row id, or None if MySQL is down."""
        if self._placeholder != "%s":
            sql = sql.replace("%s", self._placeholder)
        self._pending.append((sql, params))
        return self._flush()

    def _flush(self) -> Optional[int]:
        if not self._pending or time.time() < self._retry_at:
            return None
        last_id = None
        try:
            if self.conn is None:
                self.conn = self._connect()
                logger.info("MySQL tersambung lagi, mengirim %d baris yang tertunda.", len(self._pending))
            cur = self.conn.cursor()
            while self._pending:
                cur.execute(*self._pending[0])
                self.conn.commit()
                self._pending.popleft()
                last_id = cur.lastrowid
            return int(last_id) if last_id else None
        except Exception as e:  # MySQL stopped, network, timeout: keep analysing, retry later
            if len(self._pending) == PENDING_MAX:
                logger.error("Antrian MySQL penuh (%d baris): data tertua mulai terbuang.", PENDING_MAX)
            logger.warning("MySQL gagal (%s); %d baris ditahan, coba lagi %d dtk.", e, len(self._pending), RETRY_SECONDS)
            self._disconnect()
            self._retry_at = time.time() + RETRY_SECONDS
            return None

    def _disconnect(self) -> None:
        try:
            if self.conn is not None:
                self.conn.close()
        except Exception:
            pass
        self.conn = None

    def add_visit(
        self,
        track_id: int,
        entered_at: float,
        exited_at: float,
        entry_side: Optional[str],
        gender_est: Optional[str] = None,
        gender_conf: Optional[float] = None,
        role: str = "customer",
    ) -> Optional[int]:
        return self._write(
            "INSERT INTO visits (track_id, entered_at, exited_at, entry_side, gender_est, gender_conf, total_seconds, role)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (track_id, _dt(entered_at), _dt(exited_at), entry_side, gender_est, gender_conf,
             round(exited_at - entered_at, 2), role),
        )

    def add_zone_event(self, track_id: int, zone_name: str, enter_at: float, exit_at: float, is_sitting: bool) -> Optional[int]:
        return self._write(
            "INSERT INTO zone_events (track_id, zone_name, enter_at, exit_at, seconds, is_sitting) VALUES (%s, %s, %s, %s, %s, %s)",
            (track_id, zone_name, _dt(enter_at), _dt(exit_at), round(exit_at - enter_at, 2), int(is_sitting)),
        )

    def add_line_crossing(self, track_id: int, direction: str, entry_side: Optional[str], crossed_at: float) -> Optional[int]:
        return self._write(
            "INSERT INTO line_crossings (track_id, direction, entry_side, crossed_at) VALUES (%s, %s, %s, %s)",
            (track_id, direction, entry_side, _dt(crossed_at)),
        )

    def add_activity(self, track_id: int, activity: str, start_at: float, end_at: float) -> Optional[int]:
        return self._write(
            "INSERT INTO activity_events (track_id, activity, start_at, end_at, seconds) VALUES (%s, %s, %s, %s, %s)",
            (track_id, activity, _dt(start_at), _dt(end_at), round(end_at - start_at, 2)),
        )

    def add_alert(self, alert_type: str, zone_name: Optional[str], created_at: float, snapshot: Optional[str]) -> Optional[int]:
        return self._write(
            "INSERT INTO alerts (type, zone_name, created_at, snapshot_path_blurred) VALUES (%s, %s, %s, %s)",
            (alert_type, zone_name, _dt(created_at), snapshot),
        )

    def open_table_session(self, table_zone: str, seated_at: float) -> Optional[int]:
        return self._write("INSERT INTO table_sessions (table_zone, seated_at) VALUES (%s, %s)", (table_zone, _dt(seated_at)))

    def close_table_session(self, session_id: int, left_at: float) -> None:
        self._write("UPDATE table_sessions SET left_at = %s WHERE id = %s", (_dt(left_at), session_id))

    def set_food_arrived(self, session_id: int, arrived_at: float, wait_seconds: float) -> None:
        """Used by the food detector (restaurant stage). Only the first arrival counts."""
        self._write(
            "UPDATE table_sessions SET food_arrived_at = %s, wait_seconds = %s WHERE id = %s AND food_arrived_at IS NULL",
            (_dt(arrived_at), round(wait_seconds, 2), session_id),
        )

    def set_live(self, stats: dict) -> None:
        """Current counters for the dashboard's "Saat ini" panel (one row, id 1)."""
        self._write(
            "REPLACE INTO live_status (id, people_now, laptop_now, count_in, count_out, fps, updated_at)"
            " VALUES (1, %s, %s, %s, %s, %s, %s)",
            (stats.get("people_now", 0), stats.get("laptop_now", 0), stats.get("count_in", 0), stats.get("count_out", 0),
             stats.get("fps"), _dt(time.time())),
        )

    # ------------------------------------------------------------------ backup
    def backup(self, dest_dir: str | Path, keep_days: int = 14) -> Path:
        """mysqldump of the analytics tables (not user accounts): one .sql per day + rcis_latest.sql; old dailies deleted."""
        s = self._settings
        dump = os.environ.get("RCIS_MYSQLDUMP") or shutil.which("mysqldump") or XAMPP_MYSQLDUMP
        dest = Path(dest_dir).expanduser()
        dest.mkdir(parents=True, exist_ok=True)
        daily = dest / f"rcis_{datetime.now():%Y-%m-%d}.sql"
        with open(daily, "wb") as out:
            subprocess.run(
                [dump, "-h", s["host"], "-P", str(s["port"]), "-u", s["user"], "--single-transaction",
                 "--skip-comments", s["database"], *ANALYTICS_TABLES],
                stdout=out, stderr=subprocess.PIPE, check=True, timeout=120,
                env={**os.environ, "MYSQL_PWD": s["password"]},  # not on the command line, so `ps` cannot show it
            )
        shutil.copy2(daily, dest / "rcis_latest.sql")
        for old in sorted(dest.glob("rcis_????-??-??.sql"))[:-keep_days]:  # names sort by date
            old.unlink()
        return daily

    def close(self) -> None:
        self._retry_at = 0.0
        self._flush()
        if self._pending:
            logger.error("%d baris belum terkirim ke MySQL dan hilang saat program berhenti.", len(self._pending))
        self._disconnect()
