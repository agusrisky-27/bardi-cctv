"""
Video server for the Laravel dashboard (dashboard/): live annotated video (MJPEG), heatmap and
face-blurred alert photos. Statistics are served by Laravel from MySQL.

Run together with the pipeline:  python -m rcis.cli --rtsp --web

Security: without RCIS_WEB_PASSWORD the server only listens on 127.0.0.1 (this Mac).
With a password it listens on the local network so other devices on the same Wi-Fi can open the video.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import re
import secrets
import threading
import time
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

logger = logging.getLogger("rcis.web")


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


def create_app(live: Optional[LiveState] = None, exports_dir: str | Path = "data/exports",
               password: Optional[str] = None, alerts_dir: str | Path = "data/alerts") -> FastAPI:
    app = FastAPI(title="RCIS Video", docs_url=None, redoc_url=None)
    basic = HTTPBasic(auto_error=password is not None)

    def auth(creds: Optional[HTTPBasicCredentials] = Depends(basic)) -> None:
        if password is None:
            return  # localhost-only mode
        if not secrets.compare_digest(creds.password.encode(), password.encode()):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Basic"})

    @app.get("/heatmap.png", dependencies=[Depends(auth)])
    def heatmap() -> FileResponse:
        path = Path(exports_dir) / "heatmap.png"
        if not path.exists():
            raise HTTPException(404, "Heatmap belum ada")
        return FileResponse(path, headers={"Cache-Control": "no-store"})

    @app.get("/alert-snapshot/{name}", dependencies=[Depends(auth)])
    def alert_snapshot(name: str) -> FileResponse:
        path = Path(alerts_dir) / name
        # strict file-name check: no path separators, only our own face-blurred .jpg files
        if not re.fullmatch(r"[A-Za-z0-9_\-]+\.jpg", name) or not path.is_file():
            raise HTTPException(404, "Foto tidak ditemukan")
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
    logger.info("Video live untuk dashboard Laravel: %s", where)


def web_password() -> Optional[str]:
    return os.environ.get("RCIS_WEB_PASSWORD") or None
