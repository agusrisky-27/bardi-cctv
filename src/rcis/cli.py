"""
Command Line Interface (CLI) entry point for RCIS.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

from rcis.config.settings import AppConfig
from rcis.pipeline import VideoAnalyticsPipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("rcis.cli")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Restaurant CCTV Intelligence System (RCIS) - CLI Runner",
    )
    # Source options
    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--video",
        type=str,
        help="Path to an input video file (.mp4, .avi, etc.)",
    )
    source_group.add_argument(
        "--webcam",
        type=int,
        help="Device index of local webcam (e.g. 0, 1)",
    )
    source_group.add_argument(
        "--rtsp",
        type=str,
        help="RTSP network stream URL",
    )

    # Configuration overrides
    parser.add_argument(
        "--camera-config",
        type=str,
        default="configs/camera.example.yaml",
        help="Path to camera configuration YAML",
    )
    parser.add_argument(
        "--detection-config",
        type=str,
        default="configs/detection.yaml",
        help="Path to detection/tracking configuration YAML",
    )
    parser.add_argument(
        "--device",
        type=str,
        choices=["mps", "cpu", "cuda"],
        help="Override compute target device (mps, cpu, cuda)",
    )
    parser.add_argument(
        "--conf",
        type=float,
        help="Confidence threshold for person detection [0.0 - 1.0]",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Path to export annotated video (.mp4)",
    )
    parser.add_argument(
        "--display",
        action="store_true",
        help="Display live annotated GUI window (requires graphical desktop)",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        help="Stop processing after reaching this number of frames",
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Loop video file continuously",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # Load configuration
    config = AppConfig.load(
        camera_config_path=args.camera_config,
        detection_config_path=args.detection_config,
    )

    # Apply CLI argument overrides
    if args.video:
        config.camera.source_type = "file"
        config.camera.file.path = args.video
    elif args.webcam is not None:
        config.camera.source_type = "webcam"
        config.camera.webcam.device_index = args.webcam
    elif args.rtsp:
        config.camera.source_type = "rtsp"
        config.camera.rtsp.url = args.rtsp

    if args.loop:
        config.camera.file.loop = True

    if args.device:
        config.detection.device = args.device

    if args.conf is not None:
        config.detection.confidence_threshold = args.conf

    # Instantiate and run pipeline
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
