# src/config.py
import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="[%(levelname)s/%(asctime)s] %(message)s")
logger = logging.getLogger(__name__)

dotenv_path = Path(__file__).resolve().parent.parent / '.env'
if not dotenv_path.exists():
    logger.critical(f"ERROR: .env not found {dotenv_path}.")
    sys.exit(1)

load_dotenv(dotenv_path=dotenv_path, encoding='utf-8-sig', verbose=True)
logger.info(f"Config saved: {dotenv_path}")

REQUIRED_VARS = [
    "TELEGRAM_API_ID", "TELEGRAM_API_HASH", "DB_HOST", "DB_NAME",
    "DB_USER", "DB_PASSWORD", "DB_PORT", "SOURCE_CHANNELS"
]

missing_vars = [var for var in REQUIRED_VARS if not os.getenv(var)]
if missing_vars:
    logger.critical(f"ERROR variables .env: {missing_vars}")
    sys.exit(1)

TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

SOURCE_CHANNELS = [
    channel.strip() for channel in os.getenv("SOURCE_CHANNELS", "").split(",") if channel.strip()
]

SAFE_DELAY_SECONDS = 1.5
MEDIA_DIR = Path("media")
MEDIA_DIR.mkdir(exist_ok=True)