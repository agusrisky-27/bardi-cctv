# Testing & Validation Strategy

The **Restaurant CCTV Intelligence System (RCIS)** enforces rigorous, reproducible testing across multiple layers.

---

## 1. Testing Hierarchy

1. **Unit Testing (`tests/unit/`)**:
   - Configuration validation (Pydantic schema constraints).
   - Video Source interface compliance and error handling on non-existent files.
   - Detector abstraction handling empty frames and invalid inputs.
   - Tracker ID persistence and Kalman filter state transitions.
   - Geometry calculations (footpoint coordinate derivation).
2. **Integration Testing (`tests/integration/`)**:
   - Synthetic end-to-end video pipeline: generates a synthetic MP4 video with moving geometric objects and verifies that the video source, detector, tracker, and visualizer execute without runtime exceptions or memory leaks.
3. **Performance & Profiling**:
   - FPS benchmarks on Apple Silicon MPS vs CPU.
   - Latency breakdowns: Video decode time, detection inference time, tracking update time, visual rendering time.
   - Memory consumption tracking via `psutil`.

---

## 2. Running the Test Suite

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all unit and integration tests
pytest

# Run tests with detailed verbosity and console output
pytest -v -s

# Run only unit tests
pytest tests/unit/
```
