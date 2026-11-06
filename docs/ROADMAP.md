# Development Roadmap

This roadmap documents the phased engineering progression of the **Restaurant CCTV Intelligence System (RCIS)**.

---

## Roadmap Phases & Acceptance Criteria

### Phase 0: Discovery, Environment & Architecture (Current)
- [x] Workspace inspection and environment verification on Apple Silicon M4.
- [x] Python 3.12, PyTorch 2.15, OpenCV 5.0, Ultralytics 8.4, and Supervision 0.31 validation.
- [x] Official license and dependency assessment (AGPL vs MIT, privacy boundaries).
- [x] Project architecture and documentation suite (`ARCHITECTURE.md`, `ROADMAP.md`, `TECH_STACK.md`, `PRIVACY.md`, `DECISIONS.md`).
- **Acceptance Criteria**: All baseline docs committed; runtime environment verified with active Apple Silicon MPS acceleration.

### Phase 1: Video Ingestion & Camera Discovery (Current)
- [x] Abstract `BaseVideoSource` interface with context manager support.
- [x] `FileVideoSource` with frame seeking, metadata extraction, and clean EOF handling.
- [x] `WebcamSource` with camera index resolution.
- [x] `RTSPSource` adapter stub with reconnect logic and URL safety.
- [x] `scripts/inspect_camera.py` for hardware probing and camera discovery.
- **Acceptance Criteria**: Seamless frame reading from test video files and webcams without AI dependencies; stable FPS reporting.

### Phase 2: Person Detection Engine (Current)
- [x] Abstract `BaseDetector` interface.
- [x] Ultralytics YOLO detector (`yolo11n.pt` / `yolo11s.pt`) filtering strictly for class `0` (`person`).
- [x] Configurable confidence threshold, IOU threshold, and compute device (`mps`, `cpu`).
- [x] Output standardized to `supervision.Detections`.
- **Acceptance Criteria**: Model detects humans on sample video frames, measures inference latency, and exposes configurable thresholds.

### Phase 3: Temporal Tracking & Trajectory (Current)
- [x] Abstract `BaseTracker` interface.
- [x] ByteTrack integration via `supervision.ByteTrack`.
- [x] Footpoint anchor calculation (bottom-center of bounding box).
- [x] Trajectory history buffer and visual trail rendering.
- [x] Temporary tracking ID lifecycle management.
- **Acceptance Criteria**: Objects retain consistent integer IDs across frames; occlusion recovery verified on sample videos; FPS & memory profiled.

### Phase 4: People Counting & Directional Flow (Next Milestone)
- [ ] Virtual line crossing detection with hysteresis.
- [ ] In/Out directional vector validation.
- [ ] Duplicate crossing suppression (anti-bounce filter).
- [ ] Hourly and daily visitor statistics aggregation.
- **Acceptance Criteria**: Comparison between manual counting ground truth and automated counts on benchmark video footage.

### Phase 5: Zone Analytics & Heatmap
- [ ] Polygon zone configuration format (JSON/YAML).
- [ ] Point-in-polygon occupancy calculation per zone.
- [ ] Zone entry, dwell time, and zone exit event emitters.
- [ ] Gaussian spatial heatmap accumulation.
- **Acceptance Criteria**: Custom zones (Entrance, Dining, Waiting, Cashier) accurately report occupancy and dwell duration.

### Phase 6: Analytics Dashboard & REST API
- [ ] FastAPI backend service exposing REST endpoints and Server-Sent Events (SSE).
- [ ] SQLite database schema for cameras, zones, and aggregated events.
- [ ] Frontend React/TypeScript operational dashboard.
- [ ] Visual charts for hourly footfall, zone utilization, and average dwell times.
- **Acceptance Criteria**: Real-time dashboard updates reflecting live or simulated video stream analytics.

### Phase 7: Service Time Analytics
- [ ] Queue zone monitoring and waiting duration estimation.
- [ ] POS/KDS timestamp ingestion interface for order correlation.
- [ ] Table turnaround duration tracking.
- **Acceptance Criteria**: Explicit boundary between visual estimates and verified POS order events.

### Phase 8: Security & Operations Alerts
- [ ] Restricted zone intrusion alerts (e.g. kitchen or storage after hours).
- [ ] Maximum occupancy threshold alerts.
- [ ] Rule-based notification webhooks (Slack, Email, SMS).
- **Acceptance Criteria**: Objective threshold-based event triggers without subjective behavior profiling.

### Phase 9: Multi-Camera Architecture & Production Hardening
- [ ] Multi-camera orchestration and process isolation.
- [ ] Camera health heartbeat and automatic reconnection daemon.
- [ ] Local database archival and automated retention purge.
- [ ] Production deployment documentation and systemd/launchd configs.
