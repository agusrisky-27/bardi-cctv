#!/usr/bin/env python3
"""
Convenience script to run the RCIS pipeline on an input video file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add src to python path
src_dir = Path(__file__).resolve().parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from rcis.config.settings import AppConfig
from rcis.pipeline import VideoAnalyticsPipeline


def main() -> int:
    parser = argparse.ArgumentParser(description="RCIS Video File Runner")
    parser.add_argument("video_path", type=str, help="Path to input video file (.mp4, .avi, etc.)")
    parser.add_argument("--output", "-o", type=str, default="data/exports/annotated_output.mp4", help="Export annotated video path")
    parser.add_argument("--device", "-d", type=str, default="mps", choices=["mps", "cpu", "cuda"], help="Inference device")
    parser.add_argument("--conf", "-c", type=float, default=0.35, help="Confidence threshold")
    parser.add_argument("--display", action="store_true", help="Display GUI window")
    parser.add_argument("--max-frames", "-n", type=int, default=None, help="Stop after N frames")
    parser.add_argument("--camera-config", type=str, default="configs/camera.example.yaml")
    parser.add_argument("--detection-config", type=str, default="configs/detection.yaml")

    args = parser.parse_args()

    config = AppConfig.load(
        camera_config_path=args.camera_config,
        detection_config_path=args.detection_config,
    )
    config.camera.source_type = "file"
    config.camera.file.path = args.video_path
    config.detection.device = args.device
    config.detection.confidence_threshold = args.conf

    pipeline = VideoAnalyticsPipeline(config=config)
    summary = pipeline.run(
        display=args.display,
        output_path=args.output,
        max_frames=args.max_frames,
    )

    print("\n" + "=" * 50)
    print("           RCIS RUN SUMMARY")
    print("=" * 50)
    for k, v in summary.items():
        print(f"  {k:20s}: {v}")
    print("=" * 50 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
