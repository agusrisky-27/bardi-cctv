#!/usr/bin/env python3
"""
Extract representative frames from a video recording for dataset inspection or evaluation.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys
import cv2

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rcis.extract")


def extract_frames(
    video_path: str | Path,
    output_dir: str | Path = "data/frames",
    interval_frames: int = 30,
    max_frames: int = 50,
) -> int:
    v_path = Path(video_path)
    if not v_path.exists():
        logger.error("Video file not found: %s", v_path)
        return 0

    out_d = Path(output_dir)
    out_d.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(str(v_path.resolve()))
    if not cap.isOpened():
        logger.error("Failed to open video: %s", v_path)
        return 0

    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    logger.info("Extracting from %s (%d total frames, %.1f FPS)...", v_path.name, total, fps)

    frame_idx = 0
    saved_count = 0

    while cap.isOpened() and saved_count < max_frames:
        ret, frame = cap.read()
        if not ret or frame is None:
            break

        if frame_idx % interval_frames == 0:
            frame_filename = out_d / f"{v_path.stem}_frame_{frame_idx:06d}.jpg"
            cv2.imwrite(str(frame_filename), frame)
            saved_count += 1
            logger.info("Saved: %s", frame_filename.name)

        frame_idx += 1

    cap.release()
    logger.info("Extracted %d frames to %s", saved_count, out_d.resolve())
    return saved_count


def main() -> int:
    parser = argparse.ArgumentParser(description="RCIS Frame Extraction Utility")
    parser.add_argument("video_path", type=str, help="Path to input video")
    parser.add_argument("--output-dir", "-o", type=str, default="data/frames", help="Output directory")
    parser.add_argument("--interval", "-i", type=int, default=30, help="Extract every Nth frame")
    parser.add_argument("--max", "-m", type=int, default=50, help="Maximum number of frames to extract")
    args = parser.parse_args()

    extract_frames(
        video_path=args.video_path,
        output_dir=args.output_dir,
        interval_frames=args.interval,
        max_frames=args.max,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
