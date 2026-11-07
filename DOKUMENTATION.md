# Dokumentasi Pengerjaan Project RCIS

Catatan harian pengerjaan project CCTV analitik, dari awal sampai akhir. Setiap hari kerja ditulis di bawah minggunya.

Format setiap hari: **apa yang dikerjakan**, **hasil**, dan **kendala** (jika ada).

---

## Minggu 1 — 2 s.d. 8 November 2026

### Senin, 2 November – Kamis, 5 November

Tidak ada catatan di repo. Project mulai dikerjakan hari Jumat.

### Jumat, 6 November 2026

**Dikerjakan:**
- Menyusun kerangka awal pipeline: pembaca video (file, webcam, RTSP), deteksi orang YOLO11n, tracking ByteTrack, dukungan GPU Apple (`mps`) — commit `b4a938e`.
- Menyiapkan tools pengembangan (plugin dan skill Claude Code).
- Menetapkan keputusan project:
  - melanjutkan kode di `src/rcis`;
  - semua berjalan lokal di Mac, tanpa hosting;
  - training model **dilarang** di Mac, hanya lewat notebook Google Colab;
  - aturan privasi: tanpa face recognition, crop tidak disimpan, database hanya data agregat, foto alert wajib diburamkan.
- Menulis analitik Fase 1: garis pintu (hitung masuk/keluar + sisi datang), zona, heatmap, dwell time, dan database SQLite.
- Mencoba koneksi kamera BARDI PTZ 360 lewat RTSP.

**Hasil:**
- Pipeline dasar jalan di Mac dengan file video dan webcam.

**Kendala:**
- Hook plugin `context-mode` gagal karena versi Node terlalu lama. Plugin dimatikan untuk project ini.

### Sabtu, 7 November 2026

**Dikerjakan:**
- Commit analitik Fase 1 + pembaca RTSP live (`819324b`).
- Kamera BARDI tersambung: ONVIF diaktifkan di app BARDI, URL `rtsp://admin:***@<IP>:8554/Streaming/Channels/102` (640x360, ~24 FPS). Password hanya disimpan di `.env`.
- Membuat notebook Colab:
  - `colab/train_restaurant_detector.ipynb` (class `waiter`, `plate_food`, dataset Roboflow);
  - `colab/train_gender_classifier.ipynb` (dataset PA-100K dari mirror 4TU).
- Menulis fitur Fase 3: waktu tunggu makanan, pelayan vs pelanggan, estimasi gender (voting per orang).
- Menambah fitur durasi pakai laptop (class COCO `laptop`, tanpa training).
- Membuat dashboard web FastAPI + Chart.js (menggantikan rencana Streamlit): video live, statistik, rentang hari ini/kemarin/7 hari/30 hari, password opsional untuk dibuka dari HP.
- Menambah backup database otomatis setiap jam dan saat program berhenti (`data/backups/`, disimpan 14 hari).
- Commit `a7749b5`.
- Membuat alert keamanan (`src/rcis/security.py`): zona terlarang, loitering, di luar jam kerja; foto alert dengan area kepala diburamkan; kirim ke Telegram.
- Membuat bot Telegram dan menguji pengiriman pesan (`scripts/telegram_test.py`) — commit `621012b`.
- Menambah rotasi gambar untuk kamera yang dipasang terbalik (`RCIS_CAMERA_ROTATE`) dan program tetap jalan walau belum ada `zones.yaml` — commit `2427b34`.
- Uji langsung dengan kamera di rumah.
- Memutuskan fokus ke **kasus kantor** dulu; fitur restoran dimatikan lewat config (`restaurant_path: ""`, `staff_min_tables: 0`).
- Memperbaiki jumlah orang live yang sempat terhitung 2 saat orang yang sama masuk lagi (`live_recent_seconds`) — belum di-commit.
- Menulis `docs/CHECKLIST_SENIN.md` untuk uji di kantor.
- Menyusun ulang `README.md` dan membuat file dokumentasi ini.

**Hasil:**
- Orang terdeteksi di 99% frame uji (confidence rata-rata 0.76).
- Dashboard, backup, dan alert Telegram jalan.
- 40 test otomatis lulus.

**Kendala:**
- IP kamera berubah setelah restart; ditemukan lagi lewat alamat MAC kamera.
- Chat id Telegram awalnya salah; diperbaiki lewat `getUpdates`.
- Laptop dan posisi duduk belum terdeteksi: zona belum digambar dan kamera berada di belakang orang sehingga laptop tertutup.
- Gambar kurang tajam di sub-stream 640x360.
- Database uji `data/rcis.db` sempat terhapus saat testing; data aman karena ada backup otomatis. Sejak itu testing memakai database terpisah.
- Dataset Roboflow belum bisa dicek lisensinya (403) dan Figshare sempat error 504 (diganti mirror 4TU).

### Minggu, 8 November 2026

Belum ada catatan.

---

## Minggu 2 — 9 s.d. 15 November 2026

### Senin, 9 November 2026

**Rencana:**
- Pairing ulang kamera ke Wi-Fi kantor dan catat IP baru.
- Pasang kamera serong dari samping-atas meja; bersihkan lensa.
- Gambar zona dan garis pintu.
- Jalankan `docs/CHECKLIST_SENIN.md`.

**Dikerjakan:**
-

**Hasil:**
-

**Kendala:**
-

### Selasa, 10 November 2026

**Dikerjakan:**
-

### Rabu, 11 November 2026

**Dikerjakan:**
-

### Kamis, 12 November 2026

**Dikerjakan:**
-

### Jumat, 13 November 2026

**Dikerjakan:**
-
