import math
import random
import string
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import WATERMARK_TEXT, WATERMARK_USERNAME, DESTRUCT_TIME_SECONDS

def format_file_size(size_bytes: int) -> str:
    """Format bytes into human-readable string (KB, MB, GB)."""
    if not size_bytes or size_bytes <= 0:
        return "Unknown size"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {units[i]}"

def generate_file_code(length: int = 8) -> str:
    """Generate a random alphanumeric file code."""
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choices(chars, k=length))

def get_watermark_footer() -> str:
    """Return standard watermark footer."""
    return f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n🛡️ *{WATERMARK_TEXT}*"

def build_file_caption(file_name: str, file_size: int) -> str:
    """Generate file delivery caption with prominent watermark and notice."""
    size_str = format_file_size(file_size)
    return (
        f"📂 *File:* `{file_name}`\n"
        f"📊 *Size:* `{size_str}`\n"
        f"⏳ *Access Window:* `5 Minutes (Self-Destructs)`\n"
        f"{get_watermark_footer()}"
    )

def build_destruct_warning_text(duration_seconds: int = 300) -> str:
    """Generate the prominent self-destruct alert message."""
    mins = duration_seconds // 60
    return (
        f"🚨 ⚠️ *CRITICAL SELF-DESTRUCT ALERT* ⚠️ 🚨\n\n"
        f"🔥 *THIS FILE WILL AUTOMATICALLY DESTROY ITSELF IN {mins} MINUTES!*\n"
        f"📥 *QUICKLY SAVE IT IN YOUR SAVED MESSAGES RIGHT NOW* before it disappears forever!\n\n"
        f"📌 *Quick Save Steps:*\n"
        f"• *Mobile:* Press & hold the file message ➔ Tap *Forward* ➔ Select *Saved Messages* ➔ Send!\n"
        f"• *Desktop:* Right-click the file ➔ Click *Forward* ➔ Select *Saved Messages* ➔ Send!\n"
        f"{get_watermark_footer()}"
    )

def get_file_delivery_keyboard(file_code: str = "") -> InlineKeyboardMarkup:
    """Keyboard attached to the self-destruct warning."""
    clean_username = WATERMARK_USERNAME.lstrip("@")
    keyboard = [
        [
            InlineKeyboardButton("💡 How to Save to Saved Messages", callback_data="saved_guide")
        ],
        [
            InlineKeyboardButton(f"⚡ {WATERMARK_TEXT}", url=f"https://t.me/{clean_username}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_keyboard(file_code: str, bot_username: str) -> InlineKeyboardMarkup:
    """Admin keyboard with direct share link and actions."""
    share_url = f"https://t.me/{bot_username}?start={file_code}"
    keyboard = [
        [
            InlineKeyboardButton("🔗 Copy / Open Share Link", url=share_url)
        ],
        [
            InlineKeyboardButton("⭐ Set as Default File", callback_data=f"set_def_{file_code}"),
            InlineKeyboardButton("🗑️ Delete File", callback_data=f"del_{file_code}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
