"""
Check the Roboflow datasets BEFORE training: image counts, classes, splits, license.
Only reads metadata (nothing is downloaded). Your key never leaves this Mac and is never printed.

1. Put your key in .env:  ROBOFLOW_API_KEY=xxxx   (Roboflow > Settings > API Keys)
2. Run:  python scripts/check_datasets.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rcis.config.settings import load_dotenv  # noqa: E402

DATASETS = [  # same list as colab/train_restaurant_detector.ipynb
    ("akash-tt3fk", "ramada-bytez"),
    ("insper-erh3j", "restaurant-tables-ymr9k"),
]


def main() -> None:
    load_dotenv()
    key = os.environ.get("ROBOFLOW_API_KEY")
    if not key:
        sys.exit("ROBOFLOW_API_KEY kosong di .env")
    for ws, proj in DATASETS:
        print(f"\n=== {ws}/{proj}")
        try:
            r = requests.get(f"https://api.roboflow.com/{ws}/{proj}", params={"api_key": key}, timeout=20)
        except requests.RequestException as e:
            print("  gagal terhubung:", type(e).__name__)  # not str(e): the URL contains the key
            continue
        if not r.ok:
            print(f"  HTTP {r.status_code} (dataset tidak ditemukan / key salah / tidak punya akses)")
            continue
        data = r.json()
        p = data.get("project", {})
        print("  tipe        :", p.get("type"))
        print("  gambar      :", p.get("images"), "| belum dilabeli:", p.get("unannotated"))
        print("  split       :", p.get("splits"))
        print("  lisensi     :", p.get("license", "(tidak ada di respons, cek halaman dataset)"))
        print("  jumlah versi:", len(data.get("versions", [])) or p.get("versions"))
        classes = p.get("classes") or {}
        for name, n in sorted(classes.items(), key=lambda kv: -kv[1])[:25]:
            print(f"    {name:30} {n}")
        if len(classes) > 25:
            print(f"    ... dan {len(classes) - 25} class lain")


if __name__ == "__main__":
    main()
