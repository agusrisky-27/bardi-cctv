# RCIS — CCTV Analitik (Kantor → Restoran)

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Ultralytics](https://img.shields.io/badge/YOLO-v11-yellow.svg)](https://github.com/ultralytics/ultralytics)
[![Supervision](https://img.shields.io/badge/Supervision-0.31-purple.svg)](https://supervision.roboflow.com/)

Catatan harian pengerjaan: [DOKUMENTATION.md](DOKUMENTATION.md).

---

## 1. Tentang Project

RCIS (*Restaurant CCTV Intelligence System*) adalah project magang yang mengubah rekaman kamera CCTV biasa menjadi data statistik ruangan, tanpa mengenali identitas orang.

- **Kamera:** BARDI PTZ 360, dibaca lewat RTSP (port `8554`).
- **Otak:** YOLO11n (deteksi orang dan laptop) + ByteTrack (memberi ID sementara ke tiap orang), berjalan di Mac Apple Silicon (`mps`).
- **Penyimpanan:** SQLite lokal (`data/rcis.db`) + backup otomatis per jam.
- **Tampilan:** dashboard web lokal (FastAPI + Chart.js) dan notifikasi Telegram.
- **Semua berjalan lokal di Mac.** Tidak ada hosting, video tidak dikirim ke internet, dan training model tidak pernah dijalankan di Mac (hanya di Google Colab).

### Dua tahap kasus

| Tahap | Lokasi | Yang diukur |
|---|---|---|
| **1. Kantor (sekarang)** | Ruang meeting / kantor | Jumlah orang, arah datang, lama di ruangan, area yang paling lama ditempati, durasi pakai laptop, alert keamanan, dashboard, gender (opsional) |
| **2. Restoran (nanti)** | Restoran / cafe | Semua di atas + waktu tunggu makanan, pelayan vs pelanggan |

Kode restoran (`src/rcis/restaurant.py`) sudah ada tetapi **dimatikan** lewat config (`restaurant_path: ""`). Untuk tahap restoran cukup mengubah 2 baris di `configs/detection.yaml`.

### Alur kerja sistem

```text
Kamera BARDI --RTSP--> pembaca frame --> YOLO11 (orang, laptop) --> ByteTrack (ID sementara)
   --> analitik (garis pintu, zona, dwell, heatmap, laptop, alert) --> SQLite + backup
   --> dashboard web  /  Telegram
```

### Prinsip privasi

- Tidak ada face recognition dan tidak ada identifikasi individu. ID tracker hanya berlaku selama sesi.
- Crop wajah/badan tidak pernah disimpan ke disk.
- Database hanya berisi data agregat/anonim.
- Foto alert disimpan dan dikirim **setelah area kepala diburamkan**.
- Detail: [docs/PRIVACY.md](docs/PRIVACY.md).

---

## 2. Progres Saat Ini (per 7 November 2026)

### Sudah selesai dan sudah diuji dengan kamera asli

| Fitur | Status |
|---|---|
| Koneksi kamera BARDI via RTSP (ONVIF di app BARDI, `/Streaming/Channels/102`, 640x360, ~24 FPS) | Jalan, auto-reconnect jika putus |
| Deteksi + tracking orang (YOLO11n + ByteTrack, `mps`) | Jalan, orang terdeteksi di 99% frame uji (confidence rata-rata 0.76) |
| Jumlah orang saat ini (live) | Jalan, bug hitungan ganda saat orang masuk lagi sudah diperbaiki |
| Dashboard web (video live, statistik, rentang hari ini/kemarin/7 hari/30 hari) | Jalan |
| Alert Telegram (zona terlarang, berlama-lama/loitering, di luar jam kerja) + blur kepala | Jalan, pesan tes masuk ke Telegram |
| Database SQLite + backup per jam ke `data/backups/` | Jalan |
| Rotasi gambar untuk kamera yang dipasang terbalik (`RCIS_CAMERA_ROTATE`) | Jalan |

### Sudah ditulis, belum terbukti di lokasi

| Fitur | Kendala |
|---|---|
| Garis pintu (hitung masuk/keluar + sisi datang), zona, heatmap, dwell time | Zona dan garis pintu belum digambar untuk ruangan kantor |
| Durasi pakai laptop | Laptop belum terdeteksi: kamera ada di belakang orang sehingga laptop tertutup badan |
| Gender (estimasi agregat) | Model belum dilatih (notebook Colab sudah siap) |
| Waktu tunggu makanan, pelayan vs pelanggan | Ditunda ke tahap restoran |

### Kualitas kode

- 40 unit/integration test lulus (`pytest`).
- Notebook Colab siap: `colab/train_gender_classifier.ipynb` dan `colab/train_restaurant_detector.ipynb` (belum dijalankan).
- Beberapa perbaikan terakhir (hitungan live, mode kantor) belum di-commit.

---

## 3. Yang Akan Dikerjakan

### Senin, 9 November 2026 (di kantor)

1. Pairing ulang kamera ke Wi-Fi kantor dan cari IP barunya.
2. Pasang kamera **serong dari samping-atas meja**, bukan di belakang orang. Bersihkan lensa.
3. Gambar zona dan garis pintu: `python scripts/draw_zones.py --source rtsp`.
4. Jalankan semua langkah di [docs/CHECKLIST_SENIN.md](docs/CHECKLIST_SENIN.md).

### Minggu ini

- Bandingkan stream utama `/101` dengan sub-stream `/102` untuk deteksi orang dan laptop. Pilih yang lebih baik.
- Jika laptop masih terlalu kecil di gambar, coba `detection.input_size: 960`.
- Commit dan push perubahan yang belum di-commit.
- Tentukan cara backup ke Google Drive: kirim manual lewat AirDrop ke iPhone, atau pasang Google Drive for desktop lalu isi `RCIS_BACKUP_DIR` (otomatis).
- Opsional: jalankan notebook gender di Colab, lalu taruh `gender_classifier.pt` di `models/`.

### Tahap restoran (nanti)

- Jalankan `colab/train_restaurant_detector.ipynb` (class `waiter`, `plate_food`) dan cek lisensi dataset di [docs/DATASETS.md](docs/DATASETS.md).
- Di `configs/detection.yaml`: `restaurant_path: "models/restaurant_detector.pt"` dan `staff_min_tables: 3`.
- Uji waktu tunggu makanan dan deteksi pelayan di restoran asli.
- Opsional: integrasi Frigate untuk rekaman.

---

## 4. Kelebihan dan Kekurangan

### Kelebihan

- **Privasi terjaga:** tanpa pengenalan wajah, video tidak keluar dari Mac, foto alert diburamkan.
- **Gratis dan lokal:** tidak perlu server, cloud, atau langganan.
- **Fitur kantor tanpa training:** orang dan laptop memakai model COCO bawaan YOLO11.
- **Real time di Mac:** memakai GPU Apple (`mps`), sekitar 50 FPS pada uji awal dengan file video di MacBook Air M4.
- **Satu file pengaturan:** semua threshold di `configs/detection.yaml`; pindah kantor ↔ restoran cukup ubah config.
- **Tahan gangguan:** kamera putus akan tersambung ulang otomatis; database di-backup setiap jam dan saat program berhenti.
- **Bisa dipantau dari HP:** dashboard lewat Wi-Fi yang sama (dengan password) dan notifikasi Telegram.
- **Teruji:** 40 test otomatis.

### Kekurangan

- **Kamera PTZ:** jika kamera diputar (manual atau auto-tracking), semua zona jadi salah dan harus digambar ulang.
- **ID tracker bisa berganti:** orang yang tertutup benda/orang lain bisa dihitung dua kali.
- **"Pakai laptop" hanya perkiraan:** artinya ada laptop di depan orang yang diam ≥ 5 detik. Sistem tidak tahu laptop benar-benar dipakai.
- **Resolusi sub-stream rendah (640x360):** laptop dan orang yang jauh sulit terdeteksi.
- **Gender hanya estimasi kasar** dan modelnya belum dilatih.
- **Blur hanya untuk orang yang terdeteksi:** orang yang tidak terdeteksi tidak ikut diburamkan.
- **Mac harus menyala terus** dan hanya mendukung satu kamera per proses.
- **IP kamera bisa berubah** setiap pindah Wi-Fi atau restart router (sebaiknya IP dikunci di router).
- **Backup masih di Mac:** belum otomatis ke Google Drive.
- **Dashboard tanpa HTTPS:** aman hanya di jaringan lokal, jangan dibuka ke internet.
- **Lisensi dataset restoran** (Roboflow) belum terverifikasi penuh.

---

## Lampiran: Cara Menjalankan

### Instalasi (sekali saja)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
cp .env.example .env
```

Isi `.env`: `RCIS_RTSP_URL`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, dan opsional `RCIS_WEB_PASSWORD`, `RCIS_BACKUP_DIR`, `RCIS_CAMERA_ROTATE`. File `.env` tidak ikut ke Git. Jangan kirim isinya ke siapa pun.

### Koneksi kamera BARDI

1. Di app BARDI, aktifkan menu **ONVIF** dan catat password-nya. Username: `admin`.
2. Tes di VLC (*File → Open Network*): `rtsp://admin:PASSWORD@<IP_KAMERA>:8554/Streaming/Channels/102`.
3. Jika tampil, salin URL itu ke `RCIS_RTSP_URL` di `.env`.

Detail: [docs/CAMERA_SETUP.md](docs/CAMERA_SETUP.md).

### Menjalankan

```bash
source .venv/bin/activate
export PYTHONPATH=src
python scripts/draw_zones.py --source rtsp
python -m rcis.cli --rtsp --web
```

- Buka dashboard di `http://127.0.0.1:8000`. Dari HP: isi `RCIS_WEB_PASSWORD`, lalu buka `http://<IP-Mac>:8000`.
- Hanya lihat riwayat (tanpa kamera): `python -m rcis.web`.
- Dari file video: `python -m rcis.cli --video data/videos/sample.mp4 --display --stride 2`.
- Dari webcam Mac: `python -m rcis.cli --webcam 0 --display`.
- Berhenti: tekan `Ctrl+C` (backup terakhir dibuat otomatis).

### Telegram

1. Di Telegram cari **@BotFather**, kirim `/newbot`, salin token ke `TELEGRAM_TOKEN` di `.env`.
2. Kirim pesan "halo" ke bot.
3. Jalankan `python scripts/telegram_test.py` untuk melihat chat id, lalu isi `TELEGRAM_CHAT_ID`.
4. Jalankan script yang sama sekali lagi: pesan tes harus masuk.

### Training (hanya di Google Colab)

1. Upload notebook dari folder `colab/` ke [colab.research.google.com](https://colab.research.google.com).
2. Runtime → Change runtime type → **T4 GPU** → Run all. Jika terputus, Run all lagi: training lanjut dari checkpoint di Drive.
3. Download file `.pt` dari `MyDrive/cctv_resto/models/` ke folder `models/` project ini.

### Test

```bash
PYTHONPATH=src pytest -q
```

### Dokumen lain

[ARCHITECTURE](docs/ARCHITECTURE.md) · [ROADMAP](docs/ROADMAP.md) · [TECH_STACK](docs/TECH_STACK.md) · [PRIVACY](docs/PRIVACY.md) · [CAMERA_SETUP](docs/CAMERA_SETUP.md) · [TESTING](docs/TESTING.md) · [DECISIONS](docs/DECISIONS.md) · [DATASETS](docs/DATASETS.md) · [CHECKLIST_SENIN](docs/CHECKLIST_SENIN.md)

> **Papan pemberitahuan di lokasi:** "AREA INI DIAWASI CCTV DAN ANALITIK ANONIM. Kamera digunakan untuk keamanan dan statistik pengunjung. Tidak ada pengenalan wajah. Tidak ada data identitas yang disimpan."
