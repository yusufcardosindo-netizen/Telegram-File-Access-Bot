import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

# Load .env file
load_dotenv(dotenv_path=ENV_PATH)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Admin IDs list (comma-separated user IDs, e.g. "12345678,87654321")
raw_admins = os.getenv("ADMIN_IDS", "").strip()
ADMIN_IDS = [int(admin_id.strip()) for admin_id in raw_admins.split(",") if admin_id.strip().isdigit()]

# Default self-destruction time: 5 minutes (300 seconds)
DESTRUCT_TIME_SECONDS = int(os.getenv("DESTRUCT_TIME_SECONDS", "300"))

# Watermark configuration
WATERMARK_TEXT = os.getenv("WATERMARK_TEXT", "Made by @VIJAYEDITOR77 on Telegram")
WATERMARK_USERNAME = os.getenv("WATERMARK_USERNAME", "@VIJAYEDITOR77")

# File storage and database paths
DB_PATH = BASE_DIR / "bot_database.db"
FILES_DIR = BASE_DIR / "files"
FILES_DIR.mkdir(parents=True, exist_ok=True)
