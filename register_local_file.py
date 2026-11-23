"""
Script to register a local file from your disk (e.g. from D: drive)
into the bot database without uploading it beforehand.
Usage:
    python register_local_file.py "D:\path\to\your\file.mp4"
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import database
import utils

def register_file(file_path: str, is_default: bool = True):
    p = Path(file_path)
    if not p.exists() or not p.is_file():
        print(f"❌ Error: File not found: {file_path}")
        return

    ext = p.suffix.lower()
    if ext in [".mp4", ".mov", ".mkv", ".avi", ".webm"]:
        file_type = "video"
    elif ext in [".jpg", ".jpeg", ".png", ".webp"]:
        file_type = "photo"
    elif ext in [".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"]:
        file_type = "audio"
    else:
        file_type = "document"

    file_code = utils.generate_file_code(8)
    file_name = p.name
    file_size = p.stat().st_size

    database.init_db()
    database.add_file(
        file_code=file_code,
        file_type=file_type,
        file_id=None,
        file_name=file_name,
        file_size=file_size,
        local_path=str(p.resolve()),
        is_default=1 if is_default else 0
    )

    print("\n" + "=" * 50)
    print(f"✅ Local File Registered Successfully!")
    print(f"📂 File Name: {file_name}")
    print(f"📊 Size: {utils.format_file_size(file_size)}")
    print(f"🏷️ Type: {file_type.capitalize()}")
    print(f"🔑 Code: {file_code}")
    print(f"⭐ Set as Default: {'Yes' if is_default else 'No'}")
    print(f"\nShare link for your bot:")
    print(f"https://t.me/<YOUR_BOT_USERNAME>?start={file_code}")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python register_local_file.py <path_to_file>")
        print('Example: python register_local_file.py "D:\\video.mp4"')
        sys.exit(1)

    path_arg = sys.argv[1]
    register_file(path_arg)
