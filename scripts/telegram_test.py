"""
Test Telegram alerts.

1. Create a bot with @BotFather in Telegram, put the token in .env as TELEGRAM_TOKEN.
2. Open your bot in Telegram and send it any message (e.g. "halo").
3. Run:  python scripts/telegram_test.py     -> prints your chat id; put it in .env as TELEGRAM_CHAT_ID
4. Run it again: it sends a test message to that chat.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from rcis.config.settings import load_dotenv  # noqa: E402


def call(method: str, **params):
    """Telegram API call. Errors are reported without printing the URL (it contains the token)."""
    try:
        r = requests.post(f"https://api.telegram.org/bot{os.environ['TELEGRAM_TOKEN']}/{method}", data=params, timeout=15)
    except requests.RequestException as e:
        sys.exit(f"Tidak bisa terhubung ke Telegram ({type(e).__name__}). Cek internet.")
    if r.status_code == 401:
        sys.exit("Token salah (HTTP 401). Salin ulang token dari @BotFather ke .env.")
    if not r.ok:
        sys.exit(f"Telegram menolak permintaan (HTTP {r.status_code}): {r.text[:200]}")
    return r.json()["result"]


def main() -> None:
    load_dotenv()
    if not os.environ.get("TELEGRAM_TOKEN"):
        sys.exit("TELEGRAM_TOKEN kosong di .env. Buat bot lewat @BotFather dulu.")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not chat_id:
        updates = call("getUpdates")
        chats = {u["message"]["chat"]["id"]: u["message"]["chat"].get("first_name", "") for u in updates if "message" in u}
        if not chats:
            sys.exit("Belum ada pesan. Buka bot kamu di Telegram, kirim 'halo', lalu jalankan script ini lagi.")
        for cid, name in chats.items():
            print(f"Chat id: {cid}  ({name})")
        sys.exit("Salin angka chat id ke .env sebagai TELEGRAM_CHAT_ID, lalu jalankan script ini lagi.")
    call("sendMessage", chat_id=chat_id, text="Tes alert CCTV Analitik: koneksi Telegram berhasil.")
    print("Pesan tes terkirim. Cek Telegram kamu.")


if __name__ == "__main__":
    main()
