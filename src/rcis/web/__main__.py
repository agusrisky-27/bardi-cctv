"""Dashboard only (history from SQLite, no live video): python -m rcis.web [--port 8000]"""

import argparse
import logging

import uvicorn

from rcis.config.settings import AppConfig, load_dotenv
from rcis.web import create_app, web_password

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
parser = argparse.ArgumentParser(description="RCIS dashboard (history only)")
parser.add_argument("--port", type=int, default=8000)
parser.add_argument("--detection-config", default="configs/detection.yaml")
args = parser.parse_args()

cfg = AppConfig.load(detection_config_path=args.detection_config).analytics
pw = web_password()
host = "0.0.0.0" if pw else "127.0.0.1"
print(f"Dashboard: http://{'<IP-Mac>' if pw else '127.0.0.1'}:{args.port}  (Ctrl+C untuk berhenti)")
uvicorn.run(create_app(cfg.db_path, None, cfg.exports_dir, pw), host=host, port=args.port, log_level="warning")
