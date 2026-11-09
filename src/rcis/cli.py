"""
Command Line Interface (CLI) entry point for RCIS.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from rcis.config.settings import AppConfig, load_dotenv
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
        nargs="?",
        const="",
        help="RTSP network stream URL (no value = RCIS_RTSP_URL from .env)",
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
        "--stride",
        type=int,
        help="Process every Nth frame (overrides analytics.frame_stride)",
    )
    parser.add_argument(
        "--zones",
        type=str,
        help="Path to zones YAML (overrides analytics.zones_path)",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Serve live video, heatmap and alert photos for the Laravel dashboard at http://127.0.0.1:PORT",
    )
    parser.add_argument("--port", type=int, default=8000, help="Video server port (with --web); dashboard RCIS_ENGINE_URL must match")
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Loop video file continuously",
    )

    return parser.parse_args()


def main() -> int:
    load_dotenv()
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
    elif args.rtsp is not None:
        config.camera.source_type = "rtsp"
        config.camera.rtsp.url = args.rtsp or os.environ.get("RCIS_RTSP_URL", "")

    if args.stride:
        config.analytics.frame_stride = args.stride
    if args.zones:
        config.analytics.zones_path = args.zones

    if args.loop:
        config.camera.file.loop = True

    if args.device:
        config.detection.device = args.device

    if args.conf is not None:
        config.detection.confidence_threshold = args.conf

    live = None
    if args.web:
        from rcis.web import LiveState, create_app, start_server, web_password

        live = LiveState()
        password = web_password()
        app = create_app(live, config.analytics.exports_dir, password, config.security.alerts_dir)
        start_server(app, args.port, password)

    # Instantiate and run pipeline
    pipeline = VideoAnalyticsPipeline(config=config, live=live)
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
