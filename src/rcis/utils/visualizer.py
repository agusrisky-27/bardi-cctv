"""
Visualization and frame annotation module for RCIS.
"""

from __future__ import annotations

from typing import List, Optional
import cv2
import numpy as np
import supervision as sv

from rcis.config.settings import VisualizationConfig
from rcis.tracking.base import calculate_footpoints
from rcis.utils.profiler import PipelineProfiler


class PipelineVisualizer:
    """
    Renders bounding boxes, tracking labels, footpoint markers,
    motion trajectories, and operational telemetry HUD onto video frames.
    """

    def __init__(
        self,
        config: Optional[VisualizationConfig] = None,
        device_name: str = "mps",
    ) -> None:
        self.config = config or VisualizationConfig()
        self.device_name = device_name

        self._box_annotator = sv.BoxAnnotator(
            thickness=self.config.box_thickness,
        )
        self._label_annotator = sv.LabelAnnotator(
            text_scale=self.config.text_scale,
            text_thickness=1,
            text_padding=3,
        )
        self._trace_annotator = sv.TraceAnnotator(
            thickness=2,
            trace_length=50,
        )

    def draw_hud(
        self,
        scene: np.ndarray,
        profiler: PipelineProfiler,
        active_tracks_count: int,
        frame_idx: int,
    ) -> np.ndarray:
        """
        Render a clean, semi-transparent telemetry overlay HUD in the top-left corner.
        """
        hud_w, hud_h = 320, 130
        overlay = scene.copy()
        cv2.rectangle(overlay, (10, 10), (10 + hud_w, 10 + hud_h), (25, 25, 25), -1)
        cv2.addWeighted(overlay, 0.75, scene, 0.25, 0, scene)
        cv2.rectangle(scene, (10, 10), (10 + hud_w, 10 + hud_h), (70, 70, 70), 1)

        # Title
        cv2.putText(
            scene,
            f"RCIS CCTV INTELLIGENCE [{self.device_name.upper()}]",
            (20, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 230, 255),
            1,
            cv2.LINE_AA,
        )

        metrics = [
            f"FPS: {profiler.fps:5.1f} | Frame: {frame_idx}",
            f"Inference: {profiler.avg_inference_ms:4.1f} ms | Track: {profiler.avg_tracking_ms:4.1f} ms",
            f"Active Persons: {active_tracks_count}",
            f"Host RAM: {profiler.memory_rss_mb:.1f} MB",
        ]

        for i, text in enumerate(metrics):
            y = 54 + (i * 20)
            cv2.putText(
                scene,
                text,
                (20, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42,
                (220, 220, 220),
                1,
                cv2.LINE_AA,
            )

        return scene

    def annotate(
        self,
        frame: np.ndarray,
        detections: sv.Detections,
        profiler: Optional[PipelineProfiler] = None,
        frame_idx: int = 0,
    ) -> np.ndarray:
        """
        Draw all enabled annotations onto the frame.
        """
        scene = frame.copy()

        if len(detections) > 0:
            # Trajectory trails
            if self.config.show_trajectories and detections.tracker_id is not None:
                scene = self._trace_annotator.annotate(scene=scene, detections=detections)

            # Bounding boxes
            if self.config.show_bounding_boxes:
                scene = self._box_annotator.annotate(scene=scene, detections=detections)

            # Labels (Track ID + Confidence)
            if self.config.show_track_ids or self.config.show_confidences:
                labels: List[str] = []
                for i in range(len(detections)):
                    parts = []
                    if self.config.show_track_ids and detections.tracker_id is not None:
                        parts.append(f"#{detections.tracker_id[i]}")
                    if self.config.show_confidences and detections.confidence is not None:
                        parts.append(f"{detections.confidence[i]:.2f}")
                    label_str = " ".join(parts) if parts else "person"
                    labels.append(label_str)

                scene = self._label_annotator.annotate(
                    scene=scene,
                    detections=detections,
                    labels=labels,
                )

            # Footpoint markers (cyan dots at bottom-center of box)
            if self.config.show_footpoints:
                footpoints = calculate_footpoints(detections.xyxy)
                for pt in footpoints:
                    cv2.circle(scene, (int(pt[0]), int(pt[1])), 4, (255, 255, 0), -1)

        # Telemetry HUD
        if self.config.show_telemetry_hud and profiler is not None:
            active_count = len(detections) if detections.tracker_id is not None else 0
            scene = self.draw_hud(scene, profiler, active_count, frame_idx)

        return scene
