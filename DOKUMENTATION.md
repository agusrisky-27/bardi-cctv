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
- Training model gender di Google Colab (`colab/train_gender_classifier.ipynb`, YOLO11n-cls, imgsz 96). Hasil `models/gender_classifier.pt`: akurasi validasi 81%.
- Uji model gender di pipeline dengan `data/videos/sample.mp4`: model termuat dan berjalan (~126 FPS). Orang di video contoh terlalu kecil (6–21% tinggi gambar, batas 25%), jadi tercatat `unknown` sesuai aturan. Uji asli menunggu kamera.

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
- Kamera dipasang di kantor. IP baru `192.168.88.244`, ditemukan lewat alamat MAC kamera.
- ONVIF dinyalakan lagi di app BARDI; password ONVIF berubah setelah pairing ulang, `.env` diperbarui.
- Membandingkan stream `/102` (640x360) dan `/101` (1920x1080), masing-masing 20 detik, dengan `input_size` 640 dan 960.
- Uji pipeline penuh ±85 detik di `/101` + `input_size 960` (DB sementara, bukan `data/rcis.db`).
- `.env` dipindah ke `/101`; `configs/detection.yaml` `input_size: 960`.

**Hasil:**

| Stream | input_size | Orang terdeteksi | Laptop terdeteksi |
|---|---|---|---|
| 102 | 640 | 88% (conf 0.73) | 44% (conf 0.50) |
| 101 | 640 | 99% (conf 0.86) | 14% (conf 0.34) |
| 102 | 960 | 100% (conf 0.85) | 2% (conf 0.35) |
| 101 | 960 | 100% (conf 0.87) | 89% (conf 0.43) |

- Pipeline `/101` + 960: 26 FPS (kamera 20 FPS), inference 33.6 ms, RAM ~1.1 GB.
- Pemakaian laptop tercatat: 4 sesi, total 93 detik.
- Gender: 4 track `male`, 16 `unknown`.

**Kendala:**
- Port RTSP 8554 sempat tertutup: ONVIF mati setelah pairing ulang.
- Login RTSP ditolak (`406 Not Acceptable`) karena password ONVIF berubah.
- Pengukuran stream dilakukan bergantian, jadi posisi orang di tiap pengukuran berbeda; angka perbandingan masih kasar.
- 20 track dalam 85 detik: perlu dicek apakah sesuai jumlah orang atau ID tracker sering berganti.
- Zona dan garis pintu belum digambar, jadi duduk/arah datang belum bisa diuji.
- Uji dashboard live dengan 3–4 orang: orang dan laptop yang dipakai terdeteksi, tetapi ID orang sering berganti (30 kunjungan tercatat, tidak ada yang ≥ 60 detik). Uji A/B `lost_track_buffer_frames` 30 vs 100 belum memberi hasil yang jelas karena isi ruangan berubah.
- Orang yang duduk di balik meja: bagian bawah kotak berhenti di permukaan meja, jadi zona meja harus digambar di area meja tepat di depan orang, bukan di lantai.

**Perbaikan (sore):**
- Mode satu ruangan: tanpa `configs/zones.yaml`, "duduk" = diam ≥ 10 detik di mana saja dalam gambar. Zona tidak wajib digambar.
- Penyambungan ID (`relink_max_distance: 0.2`): jika tracker memberi ID baru di dekat posisi terakhir ID yang baru hilang (≤ 5 detik), keduanya dianggap orang yang sama. Waktu masuk, arah datang, timer duduk, dan gender ikut tersambung.
- `lost_track_buffer_frames` 30 → 50 (~5 detik).
- Alert loitering tidak lagi terkirim ulang saat ID berganti.
- 3 test baru; total 43 test lulus.
- Analisa ruangan dari foto: meja panjang, 2 pintu (pintu kaca ke luar, pintu dalam dekat lemari), jendela besar penyebab silau. Saran: kamera tinggi di pojok ujung jendela, menghadap lemari.
- Model deteksi diganti `yolo11n` → `yolo11s` (lebih akurat untuk orang jauh/tertutup dan laptop; inferensi ~26 ms di 960, pipeline 38 FPS di video contoh).
- Tampilan live: jejak garis dimatikan; label tiap orang menampilkan lama di ruangan (`N mnt`) selain `duduk`/`laptop`.
- Dashboard: tile baru "Maks. orang bersamaan" (dari tabel `visits`). Keputusan: orang yang keluar lalu masuk lagi dihitung sebagai kunjungan baru, karena sistem tidak mengenali identitas.
- Status "duduk" dihapus dari kasus kantor (terlalu sulit dibedakan dari berdiri diam); yang diukur hanya pemakaian laptop. Logika duduk di zona meja tetap ada untuk tahap restoran (waktu tunggu makanan).
- Alert loitering dimatikan di kantor (`loiter_seconds: 0`) karena tanpa status duduk semua orang di ruang rapat akan memicu alert.
- Uji live ±150 detik setelah perbaikan: 3 kunjungan (1 orang 158 detik terbaca `male`, 2 deteksi singkat 3–4 detik), sebelumnya 20 kunjungan dalam 85 detik. Jumlah orang di ruangan saat kedua uji tidak sama, jadi perbandingan ini masih kasar.

**Dashboard multi-user (malam):**
- Keputusan: dashboard pindah ke Laravel + MySQL (XAMPP, phpMyAdmin) supaya bisa dipakai banyak akun (admin/bos dan petugas). Python tetap mesin analitik.
- Folder baru `dashboard/` (Laravel 13): login, role admin/petugas, kelola akun, halaman statistik (sama dengan dashboard lama), status live dari tabel `live_status`, video live dan heatmap dari mesin Python (`RCIS_ENGINE_URL`).
- `dashboard/database/rcis.sql` untuk diimpor lewat phpMyAdmin; dibuat dari migration Laravel dan sudah diuji impor di MariaDB 10.4 (sama dengan XAMPP).
- Python: `src/rcis/mysql_sync.py` menyalin baris baru dari SQLite ke MySQL setiap 5 detik (`RCIS_MYSQL_*` di `.env`). SQLite tetap jadi sumber utama dan backup.
- Uji ujung ke ujung dengan MariaDB sementara: video contoh, data masuk MySQL, login Laravel, statistik dan live terbaca. Test: 45 Python + 8 Laravel lulus.

**Perbaikan laptop:**
- Deteksi pakai laptop sering putus-putus. Dua penyebab: keyakinan deteksi laptop rendah (rata-rata 0.43, sering di bawah batas 0.35) dan syarat "orang diam" gagal saat orang mengetik/menggerakkan tangan.
- Batas keyakinan khusus laptop jadi 0.25 (`laptop_min_confidence`), orang tetap 0.35. Syarat "diam" dihapus; orang lewat tetap tersaring oleh syarat ≥ 5 detik.
- Kamera ternyata punya slot microSD (di bawah lensa); lensa terlihat kotor/berkabut.
- README: ditambah bagian "Cara sistem menilai" dan "Mengisi area kiri dan kanan meja".

**Penyederhanaan (malam):**
- Dashboard HTML lama (FastAPI) dihapus. Python hanya menyediakan video live, heatmap, dan foto alert untuk dashboard Laravel.
- SQLite dihapus: Python menulis langsung ke MySQL. Jika MySQL mati di tengah jalan, data ditahan di memori lalu dikirim saat MySQL hidup lagi; program menolak jalan jika MySQL mati saat mulai.
- Data lama (36 kunjungan, 5 sesi laptop) dipindah ke MySQL dan dicocokkan, baru `data/rcis.db` dan `data/backups/*.db` dihapus.
- Backup jadi `mysqldump` tabel analitik (.sql) per jam ke `data/backups/` (akun/password tidak ikut).
- Ditemukan: integration test sebelumnya menulis backup ke `data/backups` milik user. Sekarang test memakai database tiruan di memori dan folder sementara.
- Uji ujung ke ujung dengan MariaDB sementara: data, status live, dan backup .sql berhasil. 41 test Python lulus.

**Neural Engine (malam):**
- `yolo11s.pt` dikonversi ke Apple CoreML (`models/yolo11s.mlpackage`, 960 px, FP16) supaya berjalan di Neural Engine. File `.pt` tetap ada sebagai cadangan; jika `.mlpackage` dihapus, program otomatis memakai `.pt`.
- Konversi gagal di venv project (torch 2.15 terlalu baru untuk coremltools 9.0); berhasil di venv sementara dengan torch 2.7 + numpy < 2.
- Hasil di video contoh: GPU ~92% → ~16%, CPU ~25% → ~53% satu inti, 25.2 → 33.6 ms/gambar, deteksi orang sama. Pipeline 26.9 FPS (cukup; kamera 20 FPS, dianalisis tiap gambar kedua).

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
