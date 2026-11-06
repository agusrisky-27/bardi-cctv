# Restaurant CCTV Intelligence System (RCIS)

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.15-orange.svg)](https://pytorch.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-5.0-green.svg)](https://opencv.org/)
[![Ultralytics](https://img.shields.io/badge/YOLO-v11-yellow.svg)](https://github.com/ultralytics/ultralytics)
[![Supervision](https://img.shields.io/badge/Supervision-0.31-purple.svg)](https://supervision.roboflow.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

RCIS is a modular, privacy-preserving **Intelligent Video Analytics (IVA)** pipeline designed to transform standard hospitality CCTV feeds into structured operational intelligence—measuring footfall, occupancy, customer flow, service timing, and zone utilization.

---

## 1. Architectural Highlights

- **Decoupled Perception & Analytics**: Stateless object detection (`BaseDetector`) is strictly separated from temporal state tracking (`BaseTracker`) and geometric analytics.
- **Hardware-Accelerated on Apple Silicon**: Full native support for Apple Silicon Metal Performance Shaders (`mps`), achieving **> 50 FPS** real-time inference on Apple M4 hardware.
- **Privacy-Preserving by Design**:
  - **No facial recognition** or biometric templates.
  - **No demographic inference** (no gender/age classification).
  - **Session-scoped temporary IDs** only (Kalman filter track IDs are never linked to personal identities).
  - **100% On-Premise Processing**: Video streams never leave local device memory.
- **Modular Video Adapters**: Unified support for offline video files (`.mp4`, `.avi`), local USB/FaceTime webcams, and network RTSP IP cameras with automatic reconnection logic.

---

## 2. Project Structure

```text
restaurant-cctv-intelligence/
├── README.md                          # Project documentation and user guide
├── pyproject.toml                     # Package specification & build configuration
├── requirements.txt                   # Frozen production dependencies
├── .env.example                       # Environment variables template
├── .gitignore                         # Git hygiene (models & videos excluded)
│
├── configs/
│   ├── camera.example.yaml            # Camera input source definitions
│   ├── detection.yaml                 # YOLO & ByteTrack parameters
│   └── zones.example.yaml             # Polygon zones & virtual lines configuration
│
├── docs/
│   ├── ARCHITECTURE.md                # System architectural design & data flow
│   ├── ROADMAP.md                     # Milestone roadmap & acceptance criteria
│   ├── TECH_STACK.md                  # Stack evaluation & software license audit
│   ├── PRIVACY.md                     # Privacy mandates & data retention policies
│   ├── CAMERA_SETUP.md                # Hardware discovery & RTSP setup guide
│   ├── TESTING.md                     # Test strategy & validation guidelines
│   └── DECISIONS.md                   # Architecture Decision Records (ADRs)
│
├── models/
│   ├── README.md                      # Model storage instructions
│   └── yolo11n.pt                     # Pretrained YOLO11 Nano weights
│
├── data/
│   ├── videos/                        # Ingest test video files (.gitignored)
│   ├── frames/                        # Extracted review frames (.gitignored)
│   └── exports/                       # Rendered analytics outputs (.gitignored)
│
├── src/
│   └── rcis/
│       ├── __init__.py
│       ├── config/                    # Pydantic schemas & YAML loader
│       ├── video/                     # File, Webcam, & RTSP adapters
│       ├── detection/                 # YOLO person detector abstraction
│       ├── tracking/                  # ByteTrack Kalman filter tracker & footpoint engine
│       ├── utils/                     # Visualizer, Annotator & Telemetry profiler
│       ├── pipeline.py                # End-to-end pipeline coordinator
│       └── cli.py                     # Main CLI application runner
│
├── scripts/
│   ├── inspect_camera.py              # Camera discovery and device inspector
│   ├── run_video.py                   # Convenience runner for video files
│   └── extract_frames.py              # Frame extraction utility
│
└── tests/
    ├── unit/                          # Unit tests (Config, Video, Detector, Tracker)
    └── integration/                   # End-to-end synthetic pipeline integration test
```

---

## 3. Installation & Setup

### Prerequisites
- macOS Sonoma / Sequoia / newer on Apple Silicon (M1/M2/M3/M4).
- Python 3.11 or 3.12.

### Step 1: Create and Activate Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
pip install -e .
```

### Step 3: Verify Environment & Hardware Acceleration
```bash
python -c "import torch; print('MPS Active:', torch.backends.mps.is_available())"
# Expected output: MPS Active: True
```

---

## 4. Usage Guide

### A. Inspect Physical Video Hardware
Probe available cameras, default resolutions, and supported FPS:
```bash
# Scan all local cameras (built-in FaceTime camera, USB UVC webcams)
python scripts/inspect_camera.py --list-webcams

# Test an RTSP IP camera connection
python scripts/inspect_camera.py --test-rtsp "rtsp://admin:password@192.168.1.100:554/stream1"
```

### B. Run Analytics on a Video File
```bash
# Run with Apple Silicon Metal acceleration and export annotated video
python -m rcis.cli --video data/videos/sample.mp4 --device mps --output data/exports/output.mp4

# Run with GUI display window (press 'q' or ESC to exit)
python -m rcis.cli --video data/videos/sample.mp4 --display

# Limit execution to 150 frames for benchmark profiling
python -m rcis.cli --video data/videos/sample.mp4 --max-frames 150
```

### C. Run Analytics on Live Webcam
```bash
# Ingest from default webcam (index 0) with live display
python -m rcis.cli --webcam 0 --display
```

### D. Run Analytics on Network RTSP Camera
```bash
# Ingest live RTSP stream with automatic reconnect resilience
python -m rcis.cli --rtsp "rtsp://192.168.1.100:554/live/ch0" --output data/exports/rtsp_log.mp4
```

### E. Extract Sample Frames for Dataset & Quality Audits
```bash
python scripts/extract_frames.py data/videos/sample.mp4 --output-dir data/frames --interval 30 --max 10
```

---

## 5. Performance Benchmarks

Measured on **MacBook Air M4 (16 GB Unified Memory, macOS 26.2)** processing standard video at 640x640 input resolution:

| Metric | Apple Silicon Metal (`mps`) | CPU Fallback (`cpu`) | Standard CCTV Requirement |
| :--- | :--- | :--- | :--- |
| **Pipeline Throughput** | **52.7 FPS** (Peak: 65.8 FPS) | **44.0 FPS** | 15.0 - 25.0 FPS |
| **Detection Inference** | **18.4 ms** | **22.3 ms** | < 40.0 ms |
| **Tracking Update** | **0.14 ms** | **0.09 ms** | < 5.0 ms |
| **Frame Annotation** | **0.41 ms** | **0.31 ms** | < 2.0 ms |
| **Host RAM Usage** | **~647 MB** | **~550 MB** | < 4,000 MB |

---

## 6. Running Automated Tests

RCIS includes a comprehensive automated test suite spanning unit and integration tests:

```bash
# Run all tests
pytest -v

# Run with profiling & stdout
pytest -v -s
```

All 13 test cases validate configuration constraints, video source seek/EOF operations, YOLO detector contract, ByteTrack Kalman filtering persistence, and end-to-end pipeline execution on synthetic video.
