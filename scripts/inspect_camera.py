#!/usr/bin/env python3
"""
Camera Inspection & Discovery Utility for RCIS.
Probes local webcam device indices and tests network RTSP streams.
"""

from __future__ import annotations

import argparse
import logging
import sys
import cv2

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rcis.inspect")


def probe_webcams(max_index: int = 4) -> None:
    """Scan and probe local video capture indices."""
    print(f"\nScanning local webcam devices (indices 0 to {max_index})...")
    found_devices = 0

    for idx in range(max_index + 1):
        cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            found_devices += 1
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = float(cap.get(cv2.CAP_PROP_FPS))
            backend = cap.getBackendName()
            print(f"  [+] Device Index {idx}: AVAILABLE")
            print(f"      Backend    : {backend}")
            print(f"      Default Res: {w}x{h}")
            print(f"      Default FPS: {fps:.1f}")

            # Grab test frame
            ret, frame = cap.read()
            if ret and frame is not None:
                print(f"      Frame Read : SUCCESS (Array shape: {frame.shape})")
            else:
                print("      Frame Read : FAILED to read test frame")
            cap.release()
        else:
            print(f"  [-] Device Index {idx}: Not available")

    print(f"\nTotal video capture devices detected: {found_devices}\n")


def test_rtsp_stream(url: str, timeout_sec: int = 5) -> None:
    """Test connecting to an RTSP IP camera feed."""
    masked = url
    if "@" in url and "://" in url:
        prefix, rest = url.split("://", 1)
        _, host = rest.split("@", 1)
        masked = f"{prefix}://***:***@{host}"

    print(f"\nTesting RTSP IP Camera Stream: {masked}")
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        print("  [!] Connection FAILED. Check network reachability, IP address, port, and credentials.")
        return

    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(cap.get(cv2.CAP_PROP_FPS))
    print("  [+] Connection ESTABLISHED successfully.")
    print(f"      Resolution : {w}x{h}")
    print(f"      Reported FPS: {fps:.1f}")

    ret, frame = cap.read()
    if ret and frame is not None:
        print(f"      Packet Read: SUCCESS (Frame shape: {frame.shape})\n")
    else:
        print("      Packet Read: FAILED to decode first video packet.\n")
    cap.release()


def main() -> int:
    parser = argparse.ArgumentParser(description="RCIS Camera Hardware Inspector")
    parser.add_argument(
        "--list-webcams",
        action="store_true",
        help="Scan and test available USB / built-in webcam indices",
    )
    parser.add_argument(
        "--test-webcam",
        type=int,
        metavar="INDEX",
        help="Test a specific webcam index (e.g. 0)",
    )
    parser.add_argument(
        "--test-rtsp",
        type=str,
        metavar="RTSP_URL",
        help="Test an RTSP camera stream URL",
    )
    args = parser.parse_args()

    if args.list_webcams or (args.test_webcam is None and args.test_rtsp is None):
        probe_webcams()

    if args.test_webcam is not None:
        probe_webcams(max_index=args.test_webcam)

    if args.test_rtsp:
        test_rtsp_stream(args.test_rtsp)

    return 0


if __name__ == "__main__":
    sys.exit(main())
