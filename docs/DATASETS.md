# Dataset & Lisensi

Semua dataset didownload **langsung di Google Colab** (bukan di Mac). Training tidak pernah dijalankan di Mac.
Status "terverifikasi" berarti saya membaca sendiri metadata resminya; selain itu **wajib dicek sebelum dipakai di luar riset/magang**.

## Dipakai di notebook

| Dataset | Dipakai untuk | Lisensi | Status |
|---|---|---|---|
| [PA-100K gender split](https://data.4tu.nl/datasets/a6c8b6dd-0df6-4de8-806b-e745074d10a8) (4TU.ResearchData; mirror [Figshare](https://figshare.com/articles/dataset/Gender_classification_of_PA-100K_dataset_a_Pedestrian_Attribute_dataset/12763712)) | `colab/train_gender_classifier.ipynb` | Figshare mencantumkan **CC0**. Data asalnya PA-100K (Liu dkk., HydraPlus-Net); syarat penggunaan penulis asli belum saya cek | Lisensi Figshare terverifikasi (API, 2026-11-07). Gambar 75x75 px, 1 file `data.zip` 89,7 MB. Figshare HTTP 504 (2026-11-07), mirror 4TU berhasil: MD5 `cc2f2550…c81` cocok, 49.302 gambar, split bawaan train 39.797 / validation 5.009 / test 4.496 (folder `male`/`female`). Notebook memakai 4TU dulu, Figshare sebagai cadangan |
| [Ramada (waiter, food)](https://universe.roboflow.com/akash-tt3fk/ramada-bytez) | `colab/train_restaurant_detector.ipynb` | **CC BY 4.0** (wajib mencantumkan sumber) | Terverifikasi via API (2026-11-07): 470 gambar (410/40/20), Food 3766, Waiter 934 |
| [Restaurant Tables](https://universe.roboflow.com/insper-erh3j/restaurant-tables-ymr9k) | idem | **CC BY 4.0** | Terverifikasi via API: 1544 gambar (1082/310/152); dipakai: plate/bowl/tray of food (~2050), waiter 1001; class lain (table, people, QR code, cup, dll) dibuang |
| ~~[Plate & food](https://universe.roboflow.com/ktu/plate-food)~~ | **tidak dipakai** | CC BY 4.0 | Hanya 37 gambar segmentasi; piring dan makanan dilabel terpisah (dobel) |
| ~~[Food detection](https://universe.roboflow.com/restaurant-monitoring-system/food_detection-kuscy)~~ | **tidak dipakai** | - | HTTP 404 (dihapus atau privat) |

**Cek ulang kapan saja:** `python scripts/check_datasets.py` (butuh `ROBOFLOW_API_KEY` di `.env`).

**Cara cek lisensi Roboflow:** notebook detector membaca bagian `roboflow: license:` dari `data.yaml` tiap dataset yang diunduh, mencetaknya, dan menyimpannya ke `MyDrive/cctv_resto/models/DATASET_LICENSES.md`. Salin isinya ke tabel ini setelah training pertama.
Lisensi Roboflow Universe bervariasi (CC BY 4.0, CC BY-NC, Public Domain, dll). Jika ada yang **NC / non-commercial**, bobot hasil training hanya boleh dipakai untuk riset/magang, bukan produk komersial.

## Skema class detector restoran

Class dataset dipetakan otomatis (lewat kata kunci, dicetak di notebook supaya bisa dicek) menjadi:

| Class | Isi |
|---|---|
| `waiter` | waiter, waitress, staff, server |
| `plate_food` | plate, food, dish, bowl, tray, meal |

Tidak ada class `customer`: dataset Ramada tidak melabeli pengunjung (akan merusak class itu), dan orang sudah dideteksi model COCO di Mac.

Class yang tidak cocok dibuang. Jika hasil pemetaan di notebook salah, ubah `KEYWORDS` atau `DATASETS` di cell konfigurasi.

## Opsional (tidak dipakai default)

| Dataset | Catatan | Status |
|---|---|---|
| [CrowdHuman](https://www.crowdhuman.org/download.html) | Orang di keramaian/terhalang. Default **tidak perlu**: YOLO11 COCO sudah cukup untuk MVP. Notebook fine-tune tidak dibuat | Lisensi belum diverifikasi (umumnya hanya untuk riset non-komersial) |
| [Head-Detection-Yolov8](https://github.com/Owen718/Head-Detection-Yolov8) | Label kepala, berguna untuk blur wajah (Fase 4) | Belum diverifikasi |
| [Versi YOLO (Mendeley)](https://data.mendeley.com/datasets/tttr2h6pz4) | CrowdHuman format YOLO | Belum diverifikasi |
| [UPAR](https://github.com/speckean/upar_dataset) | Gabungan PA100K, PETA, RAPv2, Market1501 | Belum diverifikasi |

## Catatan etika gender

Gender hanya **estimasi statistik agregat** dari gambar tubuh, dengan akurasi terbatas dan bisa bias. Ia tidak boleh dipakai untuk mengidentifikasi atau menilai individu. Crop tidak pernah disimpan ke disk.
