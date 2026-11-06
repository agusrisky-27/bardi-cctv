# Technology Stack & License Evaluation

This document outlines the software stack selected for the **Restaurant CCTV Intelligence System (RCIS)**, detailing technical suitability, licenses, and Apple Silicon compatibility.

---

## 1. Core Stack Summary

| Component | Library / Tool | Version | License | Target Role in RCIS |
| :--- | :--- | :--- | :--- | :--- |
| **Runtime** | Python | 3.12.10 | PSF License | Core application runtime |
| **Compute Framework** | PyTorch (`torch`) | 2.15.0 | Modified BSD | Tensor operations & Apple Silicon MPS backend |
| **Vision Utilities** | OpenCV (`opencv-python`) | 5.0.0 | Apache 2.0 | Video I/O, image decoding, frame operations |
| **Object Detection** | Ultralytics YOLO (`ultralytics`) | 8.4.203 | AGPL-3.0 / Enterprise | Real-time person detection |
| **Object Tracking** | ByteTrack via `supervision` | 0.31.5 | MIT License | Temporary track ID association across frames |
| **Vision Analytics** | Roboflow Supervision | 0.31.5 | MIT License | Polygon zones, line crossing, clean visual annotation |
| **Config & Schema** | Pydantic & PyYAML | 2.14 / 6.0 | MIT License | Strict type validation, YAML configuration parsing |
| **Benchmarking** | `psutil` | 7.2.2 | BSD-3-Clause | Memory, CPU, and execution latency telemetry |
| **Testing** | `pytest` | 9.2.0 | MIT License | Automated unit and integration testing |

---

## 2. Component Evaluation & License Analysis

### A. Ultralytics YOLO (`yolo11n.pt` / `yolo11s.pt`)
- **License**: AGPL-3.0 (with commercial licensing available). Pretrained models are trained on the COCO dataset (Creative Commons Attribution 4.0 International).
- **Technical Justification**:
  - State-of-the-art inference efficiency on edge and desktop environments.
  - Native support for Apple Silicon MPS (Metal Performance Shaders) device targets.
  - Standard COCO class `0` corresponds to `person`, allowing zero-shot pretrained deployment for pedestrian monitoring without custom dataset annotation.
  - Lightweight model (`yolo11n.pt` ~5.4 MB, ~2.6M parameters) enables 60+ FPS on Apple M4 hardware.
- **Architectural Boundary**: Detection is encapsulated behind an abstract `BaseDetector` protocol. If AGPL-3.0 licensing constraints necessitate an MIT/Apache alternative in commercial deployment, the engine can be swapped with ONNX Runtime, RT-DETR, or a CoreML model without rewriting upstream analytics.

### B. Roboflow Supervision (`supervision`)
- **License**: MIT License.
- **Technical Justification**:
  - Decouples raw model outputs from analytics structures (`sv.Detections`).
  - Standardized tracker implementations including ByteTrack (`sv.ByteTrack`).
  - Native geometry algorithms for polygon zones (`sv.PolygonZone`) and line crossing (`sv.LineZone`).
  - Clean modular annotators (`sv.BoxAnnotator`, `sv.LabelAnnotator`, `sv.TraceAnnotator`).

### C. ByteTrack Tracker
- **License**: MIT License.
- **Technical Justification**:
  - High association accuracy by retaining both high-score and low-score detection candidates through two-stage association.
  - Does not require a heavy ReID appearance feature extractor (which would significantly degrade FPS on edge devices).
  - Kalman filter state handles brief camera occlusions and walking trajectories.

### D. OpenCV (`opencv-python`)
- **License**: Apache 2.0.
- **Technical Justification**:
  - Industry standard for cross-platform video capture (`cv2.VideoCapture`), RTSP network buffering, and video encoding (`cv2.VideoWriter`).
  - Supports hardware-accelerated video decoding on macOS when built with AVFoundation.

---

## 3. Hardware & Platform Compatibility (Apple Silicon M4)

- **Architecture**: Apple Silicon arm64 (MacBook Air M4, 16 GB Unified Memory).
- **Acceleration**:
  - Apple Metal Performance Shaders (`torch.device("mps")`) is verified active (`torch.backends.mps.is_available() == True`).
  - Unified memory architecture eliminates PCIe transfer bottlenecks between host CPU and GPU/NPU.
- **Thermal & Power Footprint**:
  - MacBook Air is fanless. `yolo11n` operates at low TDP (< 10W), preventing thermal throttling during continuous CCTV ingestion.
