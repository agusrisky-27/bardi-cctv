"""
End-to-end pipeline coordinator for RCIS.
"""

from __future__ import annotations

import logging
from pathlib import Path
import time
from typing import Callable, Optional
import cv2
import numpy as np
import supervision as sv

from rcis.analytics import RestaurantAnalytics, load_zones
from rcis.config.settings import AppConfig
from rcis.detection.base import BaseDetector
from rcis.detection.yolo_detector import YOLODetector
from rcis.storage import Storage
from rcis.tracking.base import BaseTracker
from rcis.tracking.byte_tracker import ByteTrackTracker
from rcis.utils.profiler import PipelineProfiler
from rcis.utils.visualizer import PipelineVisualizer
from rcis.video.base import BaseVideoSource, FrameData
from rcis.video.factory import create_video_source

logger = logging.getLogger("rcis.pipeline")


class VideoAnalyticsPipeline:
    """
    Coordinates ingestion, detection, tracking, visualization, and profiling.
    """

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        video_source: Optional[BaseVideoSource] = None,
        detector: Optional[BaseDetector] = None,
        tracker: Optional[BaseTracker] = None,
        analytics: Optional[RestaurantAnalytics] = None,
    ) -> None:
        self.config = config or AppConfig()
        self.video_source = video_source or create_video_source(self.config.camera)
        self.detector = detector or YOLODetector(self.config.detection)
        self.tracker = tracker or ByteTrackTracker(self.config.tracking)
        self.profiler = PipelineProfiler()
        self.visualizer = PipelineVisualizer(
            config=self.config.visualization,
            device_name=self.detector.device,
        )
        self.analytics = analytics
        self._t0 = time.time()  # wall clock at start; frame timestamps are offsets from it

    def _build_analytics(self) -> Optional[RestaurantAnalytics]:
        """Create zone analytics once the frame size is known (after the source opens)."""
        cfg = self.config.analytics
        meta = self.video_source.metadata
        if meta.width <= 0 or meta.height <= 0:
            logger.warning("Unknown frame size; analytics disabled.")
            return None
        zones_path = Path(cfg.zones_path)
        if not zones_path.exists():
            zones_path = Path("configs/zones.example.yaml")
            logger.warning("%s not found, using %s. Draw real zones with scripts/draw_zones.py",
                           cfg.zones_path, zones_path)
        zones, line = load_zones(zones_path, meta.width, meta.height) if zones_path.exists() else ([], None)
        logger.info("Analytics: %d zones, door line: %s, DB: %s", len(zones), line is not None, cfg.db_path)
        return RestaurantAnalytics(cfg, (meta.width, meta.height), zones, line, Storage(cfg.db_path))

    def process_frame(
        self,
        frame_data: FrameData,
    ) -> tuple[np.ndarray, sv.Detections]:
        """
        Execute detection, tracking, and annotation on a single frame while profiling latencies.
        """
        frame = frame_data.frame

        # 1. Detection
        t_det_start = time.perf_counter()
        raw_detections = self.detector.detect(frame)
        det_ms = (time.perf_counter() - t_det_start) * 1000.0

        # 2. Tracking
        t_track_start = time.perf_counter()
        tracked_detections = self.tracker.update(raw_detections)
        track_ms = (time.perf_counter() - t_track_start) * 1000.0

        # 3. Visualization
        t_vis_start = time.perf_counter()
        annotated_frame = self.visualizer.annotate(
            frame=frame,
            detections=tracked_detections,
            profiler=self.profiler,
            frame_idx=frame_data.frame_index,
        )
        if self.analytics is not None:
            self.analytics.update(tracked_detections, self._t0 + frame_data.timestamp_sec, frame)
            self.analytics.draw(annotated_frame, tracked_detections)
        vis_ms = (time.perf_counter() - t_vis_start) * 1000.0

        # Record latencies into profiler (decode_ms is passed as 0 or measured in loop)
        self.profiler.record_stage(
            decode_ms=0.0,
            inference_ms=det_ms,
            tracking_ms=track_ms,
            render_ms=vis_ms,
        )

        return annotated_frame, tracked_detections

    def run(
        self,
        display: bool = False,
        output_path: Optional[str | Path] = None,
        max_frames: Optional[int] = None,
        frame_callback: Optional[Callable[[FrameData, sv.Detections], None]] = None,
    ) -> dict:
        """
        Run the analytics pipeline over the video source.
        """
        logger.info("Starting RCIS video analytics pipeline...")

        if not self.video_source.open():
            logger.error("Failed to open video source.")
            return {}
        if self.analytics is None:
            self.analytics = self._build_analytics()
        stride = self.config.analytics.frame_stride
        last_t = self._t0

        writer: Optional[cv2.VideoWriter] = None
        if output_path:
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            meta = self.video_source.metadata
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            fps = (meta.fps if meta.fps > 0 else 25.0) / stride
            writer = cv2.VideoWriter(str(out_p.resolve()), fourcc, fps, (meta.width, meta.height))
            logger.info("Writing annotated output video to: %s", out_p)

        frames_processed = 0
        window_name = "Restaurant CCTV Intelligence System (RCIS)"

        try:
            for frame_data in self.video_source.frames():
                if max_frames and frames_processed >= max_frames:
                    logger.info("Reached maximum requested frames: %d", max_frames)
                    break
                if frame_data.frame_index % stride:
                    continue  # --stride: skip frames to keep 5-10 FPS on the Mac
                last_t = self._t0 + frame_data.timestamp_sec

                t_decode_start = time.perf_counter()
                annotated_frame, tracked_detections = self.process_frame(frame_data)

                if writer is not None:
                    writer.write(annotated_frame)

                if display:
                    cv2.imshow(window_name, annotated_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key in (ord("q"), 27):  # 'q' or ESC
                        logger.info("Pipeline stopped by user keypress.")
                        break

                if frame_callback is not None:
                    frame_callback(frame_data, tracked_detections)

                frames_processed += 1
                if frames_processed % 30 == 0:
                    summary = self.profiler.get_summary()
                    logger.info(
                        "Frame %d | FPS: %.1f | Inf: %.1f ms | Track: %.1f ms | RAM: %.1f MB",
                        frames_processed,
                        summary["fps"],
                        summary["inference_ms"],
                        summary["tracking_ms"],
                        summary["memory_rss_mb"],
                    )

        finally:
            if self.analytics is not None:
                self.analytics.finalize(last_t)
                if self.analytics.storage is not None:
                    self.analytics.storage.close()
            self.video_source.release()
            if writer is not None:
                writer.release()
            if display:
                cv2.destroyAllWindows()

        final_summary = self.profiler.get_summary()
        logger.info(
            "Pipeline completed. Processed %d frames. Avg FPS: %.1f, Avg Inf: %.1f ms, RAM: %.1f MB",
            frames_processed,
            final_summary.get("fps", 0.0),
            final_summary.get("inference_ms", 0.0),
            final_summary.get("memory_rss_mb", 0.0),
        )
        return final_summary
