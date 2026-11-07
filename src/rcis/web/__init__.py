"""
Local web dashboard: live annotated video (MJPEG) + statistics from SQLite.

Run together with the pipeline:  python -m rcis.cli --rtsp --web
Dashboard only (history, no video): python -m rcis.web

Security: without RCIS_WEB_PASSWORD the server only listens on 127.0.0.1 (this Mac).
With a password it listens on the local network so a phone on the same Wi-Fi can open it.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

logger = logging.getLogger("rcis.web")
INDEX_HTML = Path(__file__).with_name("index.html")
RANGES = ("today", "yesterday", "7d", "30d")


class LiveState:
    """Latest annotated JPEG + live counters, written by the pipeline thread, read by HTTP handlers."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jpeg: Optional[bytes] = None
        self._seq = 0
        self._stats: dict = {}

    def set(self, jpeg: bytes, stats: dict) -> None:
        with self._lock:
            self._jpeg, self._stats = jpeg, stats
            self._seq += 1

    def frame(self) -> tuple[int, Optional[bytes]]:
        with self._lock:
            return self._seq, self._jpeg

    def stats(self) -> dict:
        with self._lock:
            return dict(self._stats)


def _range_bounds(name: str, now: datetime) -> tuple[str, str, str]:
    """Return (start_iso, end_iso, bucket) where bucket is 'hour' or 'day'."""
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start, end, bucket = {
        "today": (midnight, now, "hour"),
        "yesterday": (midnight - timedelta(days=1), midnight, "hour"),
        "7d": (midnight - timedelta(days=6), now, "day"),
        "30d": (midnight - timedelta(days=29), now, "day"),
    }[name]
    fmt = "%Y-%m-%dT%H:%M:%S"
    return start.strftime(fmt), end.strftime(fmt), bucket


def query_stats(conn: sqlite3.Connection, range_name: str, now: Optional[datetime] = None) -> dict:
    """All dashboard numbers for one time range. Visits = customers only (staff excluded)."""
    start, end, bucket = _range_bounds(range_name, now or datetime.now())
    q = lambda sql, *extra: conn.execute(sql, (start, end, *extra)).fetchall()  # noqa: E731
    cust = "role = 'customer' AND entered_at >= ? AND entered_at < ?"

    visitors, avg_dwell, male, female = q(
        f"SELECT COUNT(*), AVG(total_seconds), IFNULL(SUM(gender_est='male'),0), IFNULL(SUM(gender_est='female'),0)"
        f" FROM visits WHERE {cust}")[0]
    key = "strftime('%H', entered_at)" if bucket == "hour" else "substr(entered_at, 1, 10)"
    series = dict(q(f"SELECT {key}, COUNT(*) FROM visits WHERE {cust} GROUP BY 1"))
    if bucket == "hour":
        labels = [f"{h:02d}" for h in range(24)]
    else:
        first = datetime.fromisoformat(start)
        labels = [(first + timedelta(days=d)).strftime("%Y-%m-%d") for d in range(7 if range_name == "7d" else 30)]

    laptop = q("SELECT track_id, MIN(start_at), SUM(seconds), COUNT(*) FROM activity_events"
               " WHERE activity = 'laptop' AND start_at >= ? AND start_at < ? GROUP BY track_id"
               " ORDER BY SUM(seconds) DESC LIMIT 20")
    laptop_total = q("SELECT IFNULL(SUM(seconds),0), COUNT(DISTINCT track_id) FROM activity_events"
                     " WHERE activity = 'laptop' AND start_at >= ? AND start_at < ?")[0]
    return {
        "range": range_name, "start": start, "end": end, "bucket": bucket,
        "visitors": visitors,
        "avg_dwell_seconds": round(avg_dwell or 0, 1),
        "gender": {"male": male, "female": female, "unknown": visitors - male - female},
        "series": {"labels": labels, "values": [series.get(label, 0) for label in labels]},
        "entry_sides": dict(q(f"SELECT IFNULL(entry_side,'?'), COUNT(*) FROM visits WHERE {cust} GROUP BY 1")),
        "door": dict(q("SELECT direction, COUNT(*) FROM line_crossings WHERE crossed_at >= ? AND crossed_at < ?"
                       " GROUP BY direction")),
        "zones": [
            {"zone": z, "people": n, "total_seconds": round(s or 0, 1), "sitting_seconds": round(ss or 0, 1)}
            for z, n, s, ss in q("SELECT zone_name, COUNT(DISTINCT track_id), SUM(seconds),"
                                 " SUM(CASE WHEN is_sitting THEN seconds ELSE 0 END) FROM zone_events"
                                 " WHERE enter_at >= ? AND enter_at < ? GROUP BY zone_name ORDER BY 3 DESC")
        ],
        "laptop": {
            "total_seconds": round(laptop_total[0], 1),
            "people": laptop_total[1],
            "per_person": [{"track_id": t, "first_at": f, "seconds": round(s, 1), "sessions": n}
                           for t, f, s, n in laptop],
        },
        "avg_food_wait_seconds": q("SELECT AVG(wait_seconds) FROM table_sessions"
                                   " WHERE seated_at >= ? AND seated_at < ?")[0][0],
    }


def create_app(db_path: str | Path, live: Optional[LiveState] = None,
               exports_dir: str | Path = "data/exports", password: Optional[str] = None) -> FastAPI:
    app = FastAPI(title="RCIS Dashboard", docs_url=None, redoc_url=None)
    basic = HTTPBasic(auto_error=password is not None)

    def auth(creds: Optional[HTTPBasicCredentials] = Depends(basic)) -> None:
        if password is None:
            return  # localhost-only mode
        if not secrets.compare_digest(creds.password.encode(), password.encode()):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Basic"})

    def db() -> sqlite3.Connection:
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA query_only = ON")  # the web can never alter data (mode=ro breaks on WAL databases)
        return conn

    @app.get("/", response_class=HTMLResponse, dependencies=[Depends(auth)])
    def index() -> str:
        return INDEX_HTML.read_text(encoding="utf-8")

    @app.get("/api/stats", dependencies=[Depends(auth)])
    def stats(range: str = Query("today", pattern="^(today|yesterday|7d|30d)$")) -> dict:  # noqa: A002
        if not Path(db_path).exists():
            raise HTTPException(404, "Database belum ada. Jalankan pipeline dulu.")
        conn = db()
        try:
            return query_stats(conn, range)
        finally:
            conn.close()

    @app.get("/api/live", dependencies=[Depends(auth)])
    def live_stats() -> dict:
        return {"available": live is not None, **(live.stats() if live else {})}

    @app.get("/heatmap.png", dependencies=[Depends(auth)])
    def heatmap() -> FileResponse:
        path = Path(exports_dir) / "heatmap.png"
        if not path.exists():
            raise HTTPException(404, "Heatmap belum ada")
        return FileResponse(path, headers={"Cache-Control": "no-store"})

    @app.get("/video", dependencies=[Depends(auth)])
    def video() -> StreamingResponse:
        if live is None:
            raise HTTPException(404, "Video live hanya ada saat pipeline berjalan dengan --web")

        def mjpeg():
            last = -1
            while True:
                seq, jpeg = live.frame()
                if jpeg is not None and seq != last:
                    last = seq
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
                time.sleep(0.05)

        return StreamingResponse(mjpeg(), media_type="multipart/x-mixed-replace; boundary=frame")

    return app


def start_server(app: FastAPI, port: int = 8000, password: Optional[str] = None) -> None:
    """Run uvicorn in a daemon thread so the pipeline keeps the main thread (OpenCV/MPS)."""
    import uvicorn

    host = "0.0.0.0" if password else "127.0.0.1"
    server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="warning"))
    threading.Thread(target=server.run, name="rcis-web", daemon=True).start()
    where = f"http://<IP-Mac>:{port} (password aktif)" if password else f"http://127.0.0.1:{port} (hanya Mac ini)"
    logger.info("Dashboard: %s", where)


def web_password() -> Optional[str]:
    return os.environ.get("RCIS_WEB_PASSWORD") or None
