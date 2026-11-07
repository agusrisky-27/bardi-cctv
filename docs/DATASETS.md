# Dataset & Lisensi

Semua dataset didownload **langsung di Google Colab** (bukan di Mac). Training tidak pernah dijalankan di Mac.
Status "terverifikasi" berarti saya membaca sendiri metadata resminya; selain itu **wajib dicek sebelum dipakai di luar riset/magang**.

## Dipakai di notebook

| Dataset | Dipakai untuk | Lisensi | Status |
|---|---|---|---|
| [PA-100K gender split (Figshare)](https://figshare.com/articles/dataset/Gender_classification_of_PA-100K_dataset_a_Pedestrian_Attribute_dataset/12763712) | `colab/train_gender_classifier.ipynb` | Figshare mencantumkan **CC0**. Data asalnya PA-100K (Liu dkk., HydraPlus-Net); syarat penggunaan penulis asli belum saya cek | Lisensi Figshare terverifikasi (API, 2026-11-07). Gambar 75x75 px, 1 file `data.zip` 89,7 MB. Pada 2026-11-07 server unduhan Figshare mengembalikan HTTP 504 (struktur zip belum sempat saya lihat); notebook punya retry + opsi upload manual ke Drive |
| [Ramada (waiter, food)](https://universe.roboflow.com/akash-tt3fk/ramada-bytez) | `colab/train_restaurant_detector.ipynb` | Belum diketahui | **Belum terverifikasi** (Roboflow memblokir pembacaan otomatis, HTTP 403) |
| [Restaurant Tables](https://universe.roboflow.com/insper-erh3j/restaurant-tables-ymr9k) | idem | Belum diketahui | Belum terverifikasi |
| [Plate & food](https://universe.roboflow.com/ktu/plate-food) | idem | Belum diketahui | Belum terverifikasi |
| [Food detection](https://universe.roboflow.com/restaurant-monitoring-system/food_detection-kuscy) | idem | Belum diketahui | Belum terverifikasi |

**Cara cek lisensi Roboflow:** notebook detector membaca bagian `roboflow: license:` dari `data.yaml` tiap dataset yang diunduh, mencetaknya, dan menyimpannya ke `MyDrive/cctv_resto/models/DATASET_LICENSES.md`. Salin isinya ke tabel ini setelah training pertama.
Lisensi Roboflow Universe bervariasi (CC BY 4.0, CC BY-NC, Public Domain, dll). Jika ada yang **NC / non-commercial**, bobot hasil training hanya boleh dipakai untuk riset/magang, bukan produk komersial.

## Skema class detector restoran

Class dataset dipetakan otomatis (lewat kata kunci, dicetak di notebook supaya bisa dicek) menjadi:

| Class | Isi |
|---|---|
| `waiter` | waiter, waitress, staff, server |
| `plate_food` | plate, food, dish, bowl, tray, meal (dan **semua** class dari dataset `plate-food` dan `food_detection`) |
| `customer` | customer, person, people, guest, diner (opsional, orang sudah dideteksi model COCO) |

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
