# Restaurant CCTV Intelligence System (RCIS)

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.15-orange.svg)](https://pytorch.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-5.0-green.svg)](https://opencv.org/)
[![Ultralytics](https://img.shields.io/badge/YOLO-v11-yellow.svg)](https://github.com/ultralytics/ultralytics)
[![Supervision](https://img.shields.io/badge/Supervision-0.31-purple.svg)](https://supervision.roboflow.com/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)]()

RCIS is a modular, privacy-preserving **Intelligent Video Analytics (IVA)** pipeline designed to transform standard hospitality CCTV feeds into structured operational intelligence—measuring footfall, occupancy, customer flow, service timing, and zone utilization.

---

## 0. Panduan Cepat (Prototype Lokal)

Semua berjalan lokal di Mac. Tidak ada hosting. **Training tidak pernah dijalankan di Mac** — hanya lewat notebook Colab.

### Fase 0 — Koneksi kamera BARDI

1. Pasang kamera di app BARDI Smart Home, sambungkan ke Wi-Fi yang sama dengan Mac.
2. Cari IP kamera: app BARDI (info perangkat) atau halaman admin router.
3. Cek apakah ada menu **ONVIF / RTSP** di pengaturan kamera di app. Jika ada, aktifkan dan catat user/password-nya.
   Banyak kamera BARDI (basis Tuya) **tidak** membuka RTSP; jika tidak ada menu itu, lanjut pakai webcam/video untuk uji coba.
4. Tes di VLC (*File → Open Network*):
   `rtsp://admin:PASSWORD@<IP_KAMERA>:8554/Streaming/Channels/102` (sub-stream, ringan) atau `.../101` (main).
5. Jika VLC tampil, isi `RCIS_RTSP_URL` di `.env` (salin dari `.env.example`), lalu:
   ```bash
   python scripts/inspect_camera.py --test-rtsp "$RCIS_RTSP_URL"
   ```

### Fase 1 — MVP tanpa training

```bash
source .venv/bin/activate
export PYTHONPATH=src

# 1) Gambar zona & garis pintu dari frame asli -> configs/zones.yaml
python scripts/draw_zones.py --source data/videos/sample.mp4   # atau --source 0 (webcam) / --source rtsp

# 2) Jalankan analitik
python -m rcis.cli --video data/videos/sample.mp4 --display --stride 2   # file video
python -m rcis.cli --webcam 0 --display                                  # webcam Mac (simulasi ruang meeting)
python -m rcis.cli --rtsp --display                                      # BARDI via RCIS_RTSP_URL di .env

# 3) Lihat hasil
sqlite3 data/rcis.db "SELECT * FROM hourly_stats;"
open data/exports/heatmap.png
```

Output: tabel `visits`, `zone_events`, `table_sessions`, `line_crossings`, view `hourly_stats` di `data/rcis.db`, serta `data/exports/heatmap.png`.
Semua threshold (duduk, dwell, timeout, stride) ada di bagian `analytics:` pada `configs/detection.yaml`.

> **Peringatan kamera PTZ:** analitik menganggap posisi kamera tetap. Jika kamera BARDI diputar (dari app atau auto-tracking), semua zona jadi tidak valid — matikan auto-tracking/patrol dan gambar ulang zona.

### Contoh papan pemberitahuan

> **AREA INI DIAWASI CCTV DAN ANALITIK ANONIM**
> Kamera digunakan untuk keamanan dan statistik pengunjung (jumlah, waktu kunjungan, area ramai).
> Tidak ada pengenalan wajah. Tidak ada data identitas yang disimpan.
> Pertanyaan: hubungi pengelola.

### Fase 2 — Training di Google Colab (kamu jalankan sendiri)

> Training **tidak pernah** dijalankan di Mac. Dataset didownload Colab langsung dari internet Google, jadi kecepatan Wi-Fi tidak berpengaruh ke proses training; yang melewati Wi-Fi kamu hanya download `.pt` hasilnya (puluhan MB).

1. Buka [colab.research.google.com](https://colab.research.google.com) → File → Upload notebook → pilih salah satu:
   - `colab/train_restaurant_detector.ipynb` (waiter + plate_food; butuh API key Roboflow gratis)
   - `colab/train_gender_classifier.ipynb` (PA-100K; tanpa API key)
2. Runtime → Change runtime type → **T4 GPU** → Run all. Jika terputus, Run all lagi: training lanjut dari checkpoint di Drive.
3. Hasil ada di `MyDrive/cctv_resto/models/`. Download `restaurant_detector.pt` dan `gender_classifier.pt`, taruh di folder `models/` project ini.
4. Jalankan seperti biasa. Fitur aktif otomatis jika file ada; jika tidak ada, fitur itu dilewati dengan pesan peringatan.

Ringkasan dataset dan lisensi: [docs/DATASETS.md](docs/DATASETS.md).

### Fase 3 — Memakai model hasil Colab

| Fitur | Bobot | Cara kerja |
|---|---|---|
| Waktu tunggu makanan | `models/restaurant_detector.pt` | Piring (`plate_food`) yang bertahan > 3 detik di zona meja yang sedang diduduki → `table_sessions.wait_seconds`. Piring yang sudah ada sebelum orang duduk tidak dihitung |
| Pelayan vs pelanggan | idem (`waiter`) atau zona `kind: staff` atau heuristik | Track yang tumpang tindih dengan deteksi pelayan, masuk zona staf, atau berpindah ≥ 3 meja ditandai `role = staff` dan tidak masuk statistik |
| Gender | `models/gender_classifier.pt` | Crop badan hanya di memori, voting ≥ 5 frame, `unknown` jika confidence < 0.65 atau orang terlalu kecil. Hanya label agregat yang disimpan |

Coba waktu tunggu makanan **sebelum** training dengan model COCO: lihat blok komentar `models:` di `configs/detection.yaml`.

### Dashboard web (lokal, tanpa hosting)

```bash
pip install -r requirements.txt          # sekali saja (fastapi, uvicorn)
python -m rcis.cli --rtsp --web          # analitik + dashboard: buka http://127.0.0.1:8000
python -m rcis.web                       # hanya riwayat (tanpa video live), pipeline tidak perlu jalan
```

Isi dashboard: video live dengan kotak tracker, jumlah orang saat ini, pengunjung per jam/hari, laki-laki/perempuan (estimasi), arah datang, rata-rata lama di ruangan, area paling lama ditempati, durasi pakai laptop per orang, heatmap. Rentang: hari ini, kemarin, 7 hari, 30 hari.

- **Buka dari HP:** isi `RCIS_WEB_PASSWORD` di `.env`, jalankan ulang, lalu buka `http://<IP-Mac>:8000` dari HP yang satu Wi-Fi (username bebas, password sesuai `.env`). Tanpa password, dashboard hanya bisa dibuka dari Mac ini.
- Video live **tidak direkam**. Statistik dibaca dari `data/rcis.db` (read-only).
- **Pakai laptop** = orang diam dengan laptop (class COCO `laptop`, tanpa training) di depannya ≥ 5 detik. Sistem tidak bisa tahu ke mana mata melihat.

### Alert keamanan + Telegram

Tiga aturan (threshold di bagian `security:` pada `configs/detection.yaml`):

| Alert | Pemicu |
|---|---|
| `restricted_zone` | Orang non-staf di zona `kind: restricted` (dapur/gudang), maksimal sekali per menit per zona |
| `loitering` | Orang berada ≥ 10 menit tanpa duduk di meja atau memakai laptop, sekali per orang |
| `after_hours` | Ada orang di luar `open_hour`–`close_hour` (kosong = nonaktif) |

Setiap alert: foto disimpan di `data/alerts/` **setelah bagian kepala diburamkan**, dicatat di tabel `alerts` (tampil di dashboard), dan dikirim ke Telegram jika dikonfigurasi. Blur memakai area kepala di setiap kotak orang; orang yang tidak terdeteksi tidak ikut diburamkan.

Mengaktifkan Telegram (token **jangan** dikirim ke siapa pun atau ditulis di kode):
1. Di Telegram cari **@BotFather** → `/newbot` → salin token ke `.env` sebagai `TELEGRAM_TOKEN`.
2. Buka bot-mu, kirim pesan "halo".
3. `python scripts/telegram_test.py` → muncul chat id → isi `TELEGRAM_CHAT_ID` di `.env`.
4. Jalankan script yang sama sekali lagi → pesan tes masuk ke Telegram.

---

## 1. Architectural Highlights

- **Decoupled Perception & Analytics**: Stateless object detection (`BaseDetector`) is strictly separated from temporal state tracking (`BaseTracker`) and geometric analytics.
- **Hardware-Accelerated on Apple Silicon**: Full native support for Apple Silicon Metal Performance Shaders (`mps`), achieving **> 50 FPS** real-time inference on Apple M4 hardware.
- **Privacy-Preserving by Design**:
  - **No facial recognition** or biometric templates.
  - **Gender only as an aggregate statistical estimate** (Phase 3, voted per track, limited accuracy, crops never written to disk).
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
