# Dashboard CCTV Analitik (Laravel + MySQL)

Web untuk banyak pengguna: **admin (bos)** melihat dashboard dan mengelola akun, **petugas** hanya melihat dashboard.
Data ditulis langsung ke MySQL oleh mesin analitik Python (folder induk `cctv/`). Nyalakan MySQL di XAMPP sebelum menjalankan Python.

```text
Kamera --RTSP--> Python (YOLO, tracking) --> MySQL `rcis` <-- Laravel (folder ini) <-- browser bos / petugas
                                     \--> backup .sql per jam (data/backups)
```

## Kebutuhan

- XAMPP (manager-osx): nyalakan **MySQL Database**. phpMyAdmin di `http://localhost/phpmyadmin`.
- PHP 8.3+ dan Composer dari Homebrew (`php -v`). PHP bawaan XAMPP (8.0) terlalu lama untuk Laravel 13.

## Pemasangan (sekali saja)

1. phpMyAdmin → tab **Import** → pilih `database/rcis.sql` → **Go**. Database `rcis` dan semua tabel dibuat.
2. Isi `.env` di folder ini:
   - `DB_USERNAME` / `DB_PASSWORD`: akun MySQL XAMPP (bawaan: `root`, password kosong).
   - `ADMIN_NAME`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`: akun admin pertama.
3. Buat akun admin:
   ```bash
   cd ~/Documents/cctv/dashboard
   php artisan db:seed
   ```
4. Isi `.env` di folder induk `cctv/` supaya Python menulis ke MySQL yang sama:
   `RCIS_MYSQL_HOST=127.0.0.1`, lalu `RCIS_MYSQL_USER` / `RCIS_MYSQL_PASSWORD` sama dengan langkah 2.

## Menjalankan

Terminal 1, mesin analitik:
```bash
cd ~/Documents/cctv
source .venv/bin/activate
export PYTHONPATH=src
python -m rcis.cli --rtsp --web
```

Terminal 2, dashboard:
```bash
cd ~/Documents/cctv/dashboard
php artisan serve --port=8080
```

Buka `http://127.0.0.1:8080`, masuk dengan akun admin. Akun petugas dibuat di menu **Kelola akun**.

## Catatan

- Port 8000 dipakai Python (video live), jadi Laravel memakai 8080.
- Dibuka dari HP/laptop lain di Wi-Fi yang sama: `php artisan serve --host=0.0.0.0 --port=8080`, lalu buka `http://<IP-Mac>:8080`. Supaya video live ikut tampil, isi `RCIS_WEB_PASSWORD` di `.env` Python dan ganti `RCIS_ENGINE_URL` menjadi `http://<IP-Mac>:8000` (browser akan meminta password video).
- Data hanya agregat dan anonim: tanpa wajah, tanpa nama. Orang yang keluar lalu masuk lagi dihitung sebagai kunjungan baru.
- Test: `php artisan test`.
