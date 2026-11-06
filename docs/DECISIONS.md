# Architectural Decision Records (ADRs)

This document tracks significant design choices made during the development of RCIS.

---

## ADR 001: Separation of Detection and Tracking Engines
- **Date**: 2026-11-06
- **Status**: Accepted
- **Context**: Object detectors (such as YOLO) are frame-level stateless models. Video analytics (people counting, dwell time) require temporal continuity.
- **Decision**: Decouple detection (`BaseDetector`) from tracking (`BaseTracker`). Detection models output standard bounding boxes and confidences per frame; tracking assigns and maintains temporal IDs across frames.
- **Consequences**:
  - Positive: Detector models can be benchmarked, upgraded (e.g. YOLOv8 -> YOLO11), or replaced with CoreML without touching tracking or analytics algorithms.
  - Positive: Clean unit testing of tracker algorithms using mock detection feeds.

---

## ADR 002: Selection of ByteTrack as Initial Tracker
- **Date**: 2026-11-06
- **Status**: Accepted
- **Context**: In crowded restaurant environments, people frequently occlude one another or temporarily display lower detection confidence scores. Traditional SORT drops tracks when confidence dips below detection threshold.
- **Decision**: Select ByteTrack as the default tracking engine. ByteTrack preserves low-confidence detection boxes to associate true objects during occlusions.
- **Consequences**:
  - Positive: Significantly reduces identity switches (ID switch) during pedestrian crossing events without requiring expensive ReID neural network feature extractors.
  - Positive: Native integration via `supervision.ByteTrack` operates at minimal CPU overhead (< 2ms per frame).

---

## ADR 003: Footpoint Anchor for Spatial Coordinates
- **Date**: 2026-11-06
- **Status**: Accepted
- **Context**: In elevated angled CCTV perspective (typical ceiling mounting), a person's bounding box center (chest/torso) projects onto background tables, walls, or different floor zones, distorting polygon zone membership.
- **Decision**: Standardize on the bottom-center anchor point (`footpoint` = `(x_center, y_max)`) of the bounding box for all polygon zone containment and line crossing tests.
- **Consequences**:
  - Positive: Accurately reflects where a person stands on the physical floor plane.
  - Positive: Resilient against perspective distortion when people bend over or sit down.

---

## ADR 004: Apple Silicon Metal Performance Shaders (MPS) Acceleration
- **Date**: 2026-11-06
- **Status**: Accepted
- **Context**: The development and initial edge target is an Apple Silicon M4 MacBook Air (16 GB RAM). Running PyTorch inference on CPU is feasible but taxes the CPU cores and lowers FPS.
- **Decision**: Configure PyTorch to target `device="mps"` when available, with automatic transparent fallback to `"cpu"`.
- **Consequences**:
  - Positive: Real-time inference exceeding 60 FPS for `yolo11n` on Apple M4 GPU cores.
  - Positive: Low energy consumption and zero fan noise.

---

## ADR 005: Decoupled Video Source Interface
- **Date**: 2026-11-06
- **Status**: Accepted
- **Context**: Camera hardware specifications are currently unknown (used camera, connection type TBD). Development must proceed immediately using offline video files and local webcams before CCTV hardware is inspected.
- **Decision**: Implement `BaseVideoSource` with concrete implementations: `FileVideoSource`, `WebcamSource`, and `RTSPSource`.
- **Consequences**:
  - Positive: Upstream pipeline treats all sources identically through a unified iterator/generator interface.
  - Positive: Automated testing can feed reproducible synthetic video files without physical hardware.
