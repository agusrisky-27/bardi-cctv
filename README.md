# RCIS — CCTV Analitik (Kantor → Restoran)

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Ultralytics](https://img.shields.io/badge/YOLO-v11-yellow.svg)](https://github.com/ultralytics/ultralytics)
[![Supervision](https://img.shields.io/badge/Supervision-0.31-purple.svg)](https://supervision.roboflow.com/)

Catatan harian pengerjaan: [DOKUMENTATION.md](DOKUMENTATION.md).

---

## 1. Tentang Project

RCIS (*Restaurant CCTV Intelligence System*) adalah project magang yang mengubah rekaman kamera CCTV biasa menjadi data statistik ruangan, tanpa mengenali identitas orang.

- **Kamera:** BARDI PTZ 360, dibaca lewat RTSP (port `8554`).
- **Otak:** YOLO11s (deteksi orang dan laptop) + ByteTrack (memberi ID sementara ke tiap orang), berjalan di Mac Apple Silicon (`mps`).
- **Penyimpanan:** MySQL (XAMPP, database `rcis`) yang dipakai bersama dashboard, + backup `.sql` otomatis per jam di `data/backups/`.
- **Tampilan:** dashboard Laravel + MySQL multi-akun (admin/bos dan petugas) di [dashboard/](dashboard/README.md), dan notifikasi Telegram. Program Python hanya menyediakan video live, heatmap, dan foto alert untuk dashboard itu.
- **Semua berjalan lokal di Mac.** Tidak ada hosting, video tidak dikirim ke internet, dan training model tidak pernah dijalankan di Mac (hanya di Google Colab).

### Dua tahap kasus

| Tahap | Lokasi | Yang diukur |
|---|---|---|
| **1. Kantor (sekarang)** | Ruang meeting / kantor | Jumlah orang, gender, lama di ruangan, durasi pakai laptop, waktu di sisi kiri vs kanan meja, arah datang, alert keamanan |
| **2. Restoran (nanti)** | Restoran / cafe | Semua di atas + waktu tunggu makanan, pelayan vs pelanggan |

Kode restoran (`src/rcis/restaurant.py`) sudah ada tetapi **dimatikan** lewat config (`restaurant_path: ""`). Untuk tahap restoran cukup mengubah 2 baris di `configs/detection.yaml`.

### Alur kerja sistem

```text
Kamera BARDI --RTSP--> pembaca frame --> YOLO11 (orang, laptop) --> ByteTrack (ID sementara)
   --> analitik (zona kiri/kanan, lama di ruangan, heatmap, laptop, alert) --> MySQL + backup .sql
   --> MySQL --> dashboard Laravel (bos / petugas)   dan   Telegram
```

### Cara sistem menilai

| Yang diukur | Kriteria |
|---|---|
| **Kunjungan** | Satu orang dari pertama terlihat sampai hilang > 5 detik. Orang yang keluar lalu masuk lagi = kunjungan baru (sistem tidak mengenali identitas). ID yang hilang sebentar lalu muncul lagi di dekat posisi yang sama tetap dianggap orang yang sama |
| **Maks. orang bersamaan** | Jumlah orang terbanyak di ruangan pada saat yang sama; perkiraan jumlah orang berbeda per hari |
| **Lama di ruangan** | Selisih waktu pertama dan terakhir terlihat |
| **Pakai laptop** | Laptop terdeteksi (keyakinan ≥ 0.25) dengan titik tengahnya di dalam kotak orang yang diperlebar 30%, bertahan ≥ 5 detik. Laptop yang hilang ≤ 5 detik (tertutup tangan) tidak memutus sesi. Sistem tidak tahu apakah layar benar-benar dilihat |
| **Sisi kiri / kanan** | Titik bawah kotak orang berada di dalam zona `sisi_kiri` atau `sisi_kanan`; dicatat berapa menit dan berapa orang |
| **Gender** | Estimasi dari ≥ 5 frame per orang; `unknown` jika ragu (< 0.65) atau orang terlalu kecil di gambar |

### Mengisi area kiri dan kanan meja

Dilakukan sekali setelah kamera dipasang permanen. Ulangi jika kamera digeser atau diputar.

1. Jalankan (program analitik harus berhenti dulu):
   ```bash
   cd ~/Documents/cctv
   source .venv/bin/activate
   python scripts/draw_zones.py --source rtsp
   ```
2. Muncul foto dari kamera. Klik titik-titik mengelilingi **separuh meja sisi kiri beserta kursinya** (minimal 4 titik). Batas kanannya = garis tengah meja.
3. Tekan `n`. Di Terminal ketik nama `sisi_kiri`, Enter, lalu jenis `area`, Enter.
4. Klik jendela foto lagi, lakukan hal yang sama untuk separuh kanan dengan nama `sisi_kanan`.
5. Tekan `s` untuk menyimpan ke `configs/zones.yaml`. Salah klik: `u` (hapus titik terakhir), `q` (keluar tanpa menyimpan).
6. Jalankan lagi `python -m rcis.cli --rtsp --web`. Hasilnya di grafik **"Area paling lama ditempati (menit)"**.

Tips: zona harus mencakup **permukaan meja di depan kursi**, bukan hanya lantai, karena kaki orang yang duduk tertutup meja sehingga bagian bawah kotaknya berhenti di tepi meja.

### Prinsip privasi

- Tidak ada face recognition dan tidak ada identifikasi individu. ID tracker hanya berlaku selama sesi.
- Crop wajah/badan tidak pernah disimpan ke disk.
- Database hanya berisi data agregat/anonim.
- Foto alert disimpan dan dikirim **setelah area kepala diburamkan**.
- Detail: [docs/PRIVACY.md](docs/PRIVACY.md).

---

## 2. Progres Saat Ini (per 9 November 2026)

### Sudah selesai dan sudah diuji dengan kamera asli di kantor

| Fitur | Status |
|---|---|
| Koneksi kamera BARDI via RTSP (ONVIF di app BARDI, stream utama `/Streaming/Channels/101`, 1920x1080, ~20 FPS) | Jalan, auto-reconnect jika putus |
| Deteksi + tracking orang (YOLO11n + ByteTrack, `mps`, `input_size 960`) | Jalan, orang terdeteksi di 100% frame uji (confidence rata-rata 0.87), ~26 FPS |
| Durasi pakai laptop | Jalan, laptop terdeteksi di 89% frame uji setelah kamera dipindah serong dari atas |
| Jumlah orang saat ini (live) | Jalan |
| Dashboard web (video live, statistik, rentang hari ini/kemarin/7 hari/30 hari) | Jalan |
| Dashboard Laravel + MySQL multi-user (admin/bos, petugas) di `dashboard/` | Sudah dibuat dan diuji dengan MariaDB sementara; belum dipasang di XAMPP. Panduan: [dashboard/README.md](dashboard/README.md) |
| Alert Telegram (zona terlarang, berlama-lama/loitering, di luar jam kerja) + blur kepala | Jalan, pesan tes masuk ke Telegram |
| Database MySQL + backup `.sql` per jam ke `data/backups/` | Sudah diuji dengan MariaDB sementara |
| Rotasi gambar untuk kamera yang dipasang terbalik (`RCIS_CAMERA_ROTATE`) | Jalan |

### Sudah ditulis, masih perlu diuji lebih lama

| Fitur | Catatan |
|---|---|
| Lama di ruangan dan jumlah pengunjung | ID orang sempat sering berganti; sudah diperbaiki dengan penyambungan ID (`relink_max_distance`), perlu uji ulang dengan beberapa orang |
| Arah datang | Tanpa garis pintu, arah = sisi gambar tempat orang pertama terlihat |
| Gender (estimasi agregat) | Model dilatih di Colab (akurasi validasi 81%); di kamera sebagian besar masih `unknown` |
| Waktu tunggu makanan, pelayan vs pelanggan | Ditunda ke tahap restoran |

### Kualitas kode

- 43 unit/integration test lulus (`pytest`).
- Notebook gender sudah dijalankan; notebook detector restoran belum.

---

## 3. Yang Akan Dikerjakan

### Minggu ini

- Uji ulang hitungan pengunjung dan lama di ruangan dengan 3–4 orang yang keluar-masuk; cocokkan dengan hitungan manual.
- Uji gender di kamera. Jika banyak `unknown`, pertimbangkan menurunkan `gender_min_height_ratio`.
- Opsional: gambar zona/garis pintu (`python scripts/draw_zones.py --source rtsp`) jika butuh statistik per meja atau hitung masuk/keluar lewat pintu.
- Commit dan push perubahan yang belum di-commit.
- Tentukan cara backup ke Google Drive: kirim manual lewat AirDrop ke iPhone, atau pasang Google Drive for desktop lalu isi `RCIS_BACKUP_DIR` (otomatis).

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

- **Kamera PTZ:** jika kamera diputar (manual atau auto-tracking), zona (jika dipakai) jadi salah dan arah datang bergeser; matikan auto-tracking/patrol.
- **ID tracker bisa berganti:** orang yang tertutup benda/orang lain bisa dihitung dua kali.
- **"Pakai laptop" hanya perkiraan:** artinya ada laptop di depan orang yang diam ≥ 5 detik. Sistem tidak tahu laptop benar-benar dipakai.
- **Resolusi sub-stream rendah (640x360):** laptop dan orang yang jauh sulit terdeteksi.
- **Gender hanya estimasi kasar:** akurasi validasi 81%, dan orang yang tingginya kurang dari 25% tinggi gambar tercatat `unknown`.
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
2. Tes di VLC (*File → Open Network*): `rtsp://admin:PASSWORD@<IP_KAMERA>:8554/Streaming/Channels/101` (stream utama; `/102` = sub-stream 640x360).
3. Jika tampil, salin URL itu ke `RCIS_RTSP_URL` di `.env`.

Detail: [docs/CAMERA_SETUP.md](docs/CAMERA_SETUP.md).

### Menjalankan

```bash
source .venv/bin/activate
export PYTHONPATH=src
python scripts/draw_zones.py --source rtsp
python -m rcis.cli --rtsp --web
```

- Dashboard: jalankan Laravel di Terminal lain (`cd dashboard && php artisan serve --port=8080`), lalu buka `http://127.0.0.1:8080`. Panduan: [dashboard/README.md](dashboard/README.md).
- `--web` menyalakan video live di port 8000 untuk dashboard Laravel (`RCIS_ENGINE_URL`).
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
