# Checklist Uji Coba di Kantor

Tujuan: memasang kamera BARDI di ruang meeting, menggambar zona, lalu membuktikan bahwa hitungan program cocok dengan hitungan manual.

## A. Dibawa dari rumah

- [ ] MacBook + charger
- [ ] Kamera BARDI + adaptor listrik + kabel (colokan 5V, bukan port USB laptop)
- [ ] HP (untuk app BARDI, dan sebagai **hotspot cadangan**)
- [ ] Jarum SIM atau tusuk gigi (tombol reset kamera)
- [ ] Kain lensa atau tisu kacamata (lensa kemarin kotor)
- [ ] Penyangga kamera: tripod kecil, tumpukan buku, atau lakban (kamera perlu **tinggi**, sekitar 2 m)
- [ ] Stopwatch (bisa dari HP) dan kertas/HP untuk mencatat hasil uji

Sebelum berangkat, di rumah:
- [ ] `git pull` sudah terbaru dan `pip install -r requirements.txt` sudah dijalankan
- [ ] File `.env` ada (password kamera sudah diisi)
- [ ] Mac punya internet di kantor, karena grafik dashboard dimuat dari CDN

## B. Menyambungkan kamera di kantor

1. [ ] Sambungkan Mac ke Wi-Fi kantor.
2. [ ] Cek band Wi-Fi: tahan **Option (⌥)** lalu klik ikon Wi-Fi. Baris **Channel** harus 1–13 (2.4 GHz). Kamera tidak bisa memakai 5 GHz.
3. [ ] Colok kamera. Tunggu sampai berputar dan lampu menyala.
4. [ ] Kamera masih mengenal Wi-Fi rumah, jadi **pairing ulang**:
   - tahan tombol reset sekitar 5–10 detik (di bawah lensa, dekat slot microSD) sampai lampu **biru berkedip**
   - app BARDI → **+** → IP Camera → pilih Wi-Fi kantor → scan QR dari jarak 20–30 cm
5. [ ] Lampu biru **diam** = tersambung.
6. [ ] Di app: kamera → ⚙️ → **Onvif** → pastikan switch **menyala**, lalu catat **IP address**-nya.
7. [ ] Ganti IP di `.env` (hanya bagian angka `192.168.1.11`):
   ```
   RCIS_RTSP_URL=rtsp://admin:PASSWORD@IP_BARU:8554/Streaming/Channels/102
   ```
8. [ ] Tes: `nc -zv IP_BARU 8554` harus menjawab `succeeded`.

Kalau `Connection refused` atau ping gagal padahal kamera online di app, Wi-Fi kantor mungkin memblokir antar-perangkat (client isolation). Pakai **hotspot HP**:
- iPhone: Pengaturan → Hotspot Pribadi → nyalakan **Maksimalkan Kompatibilitas**
- Android: Hotspot → Band AP → **2.4 GHz**
- Pairing ulang kamera ke hotspot itu, sambungkan Mac ke hotspot yang sama, lalu ulangi langkah 6–8.

## C. Memasang kamera (lakukan sekali, jangan digeser lagi)

- [ ] Lap lensa.
- [ ] Letakkan **tinggi** (sekitar 2 m), miring ke bawah, supaya seluruh lantai dan **kaki orang** terlihat. Zona dan heatmap dihitung dari titik kaki.
- [ ] Hindari jendela atau lampu terang di belakang area yang dipantau (siluet gelap membuat deteksi turun).
- [ ] Di app BARDI matikan **auto-tracking / patroli** kalau ada.
- [ ] Tandai posisi kamera (foto atau lakban). Kalau bergeser, zona harus digambar ulang.

## D. Menggambar zona

```bash
source .venv/bin/activate && export PYTHONPATH=src
python scripts/draw_zones.py --source rtsp
```

- klik titik-titik di sekeliling area, tekan **n**, lalu ketik nama (misalnya `meja_1`) dan jenis (`table`)
- tekan **l** lalu klik 2 titik untuk **garis pintu** (tempat orang masuk/keluar ruangan)
- tekan **s** untuk menyimpan ke `configs/zones.yaml`
- tidak perlu zona terlarang atau kasir kalau tidak ada di ruangan

Hitungan IN/OUT terbalik? Tukar titik awal dan akhir garis pintu (gambar ulang garisnya).

## E. Menjalankan

```bash
python -m rcis.cli --rtsp --web
```

Jalankan dashboard Laravel (`cd dashboard && php artisan serve --port=8080`) lalu buka **127.0.0.1:8080**. Panduan: `dashboard/README.md`.

Catatan membaca hasil:
- Kotak "Saat ini" langsung bergerak. Angka ringkasan dan grafik baru bertambah sekitar 5 detik setelah orang **keluar dari pandangan kamera** (kunjungan dicatat saat selesai).
- Hentikan dengan **Ctrl+C**. Data tersimpan dan backup dibuat otomatis.

## F. Uji akurasi (bukti untuk laporan)

Isi kolom "manual" saat kejadian berlangsung, lalu bandingkan dengan program.

| # | Skenario | Manual | Program | Catatan |
|---|---|---|---|---|
| 1 | 10 orang masuk lewat pintu, lalu 10 orang keluar | IN 10 / OUT 10 | | |
| 2 | Orang datang dari sisi kiri / kanan / depan (3 orang tiap sisi) | | | Lihat grafik "Arah datang" |
| 3 | 3 orang duduk diam di meja selama 1 menit | 60 dtk | | Tabel `zone_events`, kolom `is_sitting` |
| 4 | 2 orang memakai laptop selama 2 menit (stopwatch) | 120 dtk | | Tabel durasi laptop di dashboard |
| 5 | Orang berjalan lewat di belakang orang lain (terhalang) | ID tetap? | | Lihat apakah ID (#) berganti |
| 6 | 1 orang keluar-masuk 3 kali | 3 | | Bisa terhitung lebih jika ID berganti |

Melihat data mentah: buka phpMyAdmin → database `rcis` → tabel `visits`, `zone_events`, `activity_events`, `line_crossings` → tab **Browse**.

Hitung selisihnya: `akurasi = 1 - |program - manual| / manual`. Catat juga kasus yang meleset (orang berkerumun, terhalang, cahaya buruk), karena itu bahan pembahasan di laporan.

## G. Masalah yang sering muncul

| Gejala | Kemungkinan penyebab | Tindakan |
|---|---|---|
| `Connection refused` ke kamera | Kamera offline, IP berubah, atau client isolation | Cek status di app, cek IP di menu Onvif, coba hotspot HP |
| Lampu biru berkedip terus | Belum tersambung ke Wi-Fi | Reset 5–10 detik, pairing ulang, pastikan Wi-Fi 2.4 GHz |
| Orang tidak terdeteksi | Gelap, backlight, atau lensa kotor | Ubah posisi, lap lensa, hindari jendela |
| Orang terdeteksi tapi zona 0 | Kaki tidak terlihat di kamera | Naikkan kamera, geser sudut ke bawah |
| IN/OUT terbalik | Arah garis pintu | Gambar ulang garis dengan titik awal dan akhir ditukar |
| Zona meleset setelah beberapa waktu | Kamera bergeser atau berputar | Matikan auto-tracking, gambar ulang zona |
| Gender selalu "Tidak diketahui" | Model belum dilatih | Normal sampai `gender_classifier.pt` ada di `models/` |
| Grafik kosong, video ada | Mac tidak punya internet (grafik dari CDN) | Sambungkan internet |

## H. Selesai

- [ ] Ctrl+C, pastikan ada baris `DB backup:`
- [ ] Screenshot dashboard (video + grafik) dan hasil tabel uji untuk laporan
- [ ] Kalau memakai OneDrive atau Drive untuk backup, isi `RCIS_BACKUP_DIR` di `.env`
- [ ] Beri tahu orang di ruangan bahwa ada kamera dan analitik anonim (contoh teks papan ada di README)
