"""
Performance profiler and system telemetry for RCIS.
"""

from __future__ import annotations

from collections import deque
import os
import time
from typing import Deque, Dict
import psutil


class PipelineProfiler:
    """
    Tracks execution latency across pipeline stages, computes FPS,
    and measures host RAM memory consumption.
    """

    def __init__(self, window_size: int = 30) -> None:
        self.window_size = window_size
        self._process = psutil.Process(os.getpid())

        # Stage durations in milliseconds
        self._decode_times: Deque[float] = deque(maxlen=window_size)
        self._inference_times: Deque[float] = deque(maxlen=window_size)
        self._tracking_times: Deque[float] = deque(maxlen=window_size)
        self._render_times: Deque[float] = deque(maxlen=window_size)
        self._total_frame_times: Deque[float] = deque(maxlen=window_size)

        self._frame_count = 0
        self._start_wall_time = time.time()
        self._last_frame_timestamp = time.time()

    def record_stage(
        self,
        decode_ms: float,
        inference_ms: float,
        tracking_ms: float,
        render_ms: float,
    ) -> None:
        """
        Record stage execution latencies for a completed frame.
        """
        self._frame_count += 1
        now = time.time()
        frame_interval_sec = now - self._last_frame_timestamp
        self._last_frame_timestamp = now

        self._decode_times.append(decode_ms)
        self._inference_times.append(inference_ms)
        self._tracking_times.append(tracking_ms)
        self._render_times.append(render_ms)

        total_pipeline_ms = decode_ms + inference_ms + tracking_ms + render_ms
        self._total_frame_times.append(total_pipeline_ms)

    @property
    def fps(self) -> float:
        """Moving average frames per second."""
        if not self._total_frame_times:
            return 0.0
        avg_frame_ms = sum(self._total_frame_times) / len(self._total_frame_times)
        return 1000.0 / avg_frame_ms if avg_frame_ms > 0 else 0.0

    @property
    def avg_inference_ms(self) -> float:
        """Moving average inference latency in milliseconds."""
        if not self._inference_times:
            return 0.0
        return sum(self._inference_times) / len(self._inference_times)

    @property
    def avg_tracking_ms(self) -> float:
        """Moving average tracker update latency in milliseconds."""
        if not self._tracking_times:
            return 0.0
        return sum(self._tracking_times) / len(self._tracking_times)

    @property
    def avg_decode_ms(self) -> float:
        """Moving average video decode latency in milliseconds."""
        if not self._decode_times:
            return 0.0
        return sum(self._decode_times) / len(self._decode_times)

    @property
    def avg_render_ms(self) -> float:
        """Moving average visualization render latency in milliseconds."""
        if not self._render_times:
            return 0.0
        return sum(self._render_times) / len(self._render_times)

    @property
    def memory_rss_mb(self) -> float:
        """Current process Resident Set Size (RSS) memory in megabytes."""
        try:
            return self._process.memory_info().rss / (1024 * 1024)
        except Exception:
            return 0.0

    @property
    def total_processed_frames(self) -> int:
        return self._frame_count

    def get_summary(self) -> Dict[str, float]:
        """
        Return structured benchmark metrics.
        """
        return {
            "fps": round(self.fps, 1),
            "inference_ms": round(self.avg_inference_ms, 2),
            "tracking_ms": round(self.avg_tracking_ms, 2),
            "decode_ms": round(self.avg_decode_ms, 2),
            "render_ms": round(self.avg_render_ms, 2),
            "memory_rss_mb": round(self.memory_rss_mb, 1),
            "total_frames": self._frame_count,
        }
