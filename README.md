# ⚡ Telegram File Access Bot with 5-Minute Self-Destruction
> **Watermark & Attribution:** *Made by @VIJAYEDITOR77 on Telegram*

A powerful and reliable Telegram bot designed for securely sharing files (videos, project files, documents, photos, audio) with an automated **5-minute self-destruction timer**. The bot explicitly guides and warns users to **quickly save the delivered file to their "Saved Messages"** before it is permanently deleted from the chat.

---

## 🌟 Key Features

- ⏳ **Automated 5-Minute Self-Destruct**:
  - Once delivered to the user, a precise 300-second (5-minute) countdown begins.
  - When the timer expires, both the file message and the alert message are automatically deleted from the chat via the Telegram Bot API.
- 📥 **"Quickly Save to Saved Messages" Guidance**:
  - Urgently alerts the recipient: *"This file will destroy itself in 5 minutes! Quickly save it in your Saved Messages right now!"*
  - Includes an interactive button with step-by-step instructions for Android, iPhone, and Desktop.
- 🛡️ **Built-in Watermark & Branding**:
  - Every message, file caption, countdown alert, and inline button proudly features:
    `Made by @VIJAYEDITOR77 on Telegram`
- 🔗 **Deep-Link File Access**:
  - Generates unique shareable links for each file: `https://t.me/YourBot?start=file_code`
  - Recipient taps the link, hits **Start**, and immediately receives the file.
- ⭐ **Default File Support**:
  - Set a primary file that any user receives if they message `/start` or `/getfile` directly.
- 💾 **Persistent SQLite Database**:
  - Stores all registered files, metadata, codes, and active countdowns.
  - **Crash-Resilient**: If the bot is restarted, active countdown timers are automatically resumed from the database so no files are left undeleted!
- 📂 **Two Easy Ways to Add Files**:
  1. **Direct Telegram Upload**: Just forward or upload any file (up to 2 GB) directly to the bot chat.
  2. **Local D-Drive Registration**: Use the included `register_local_file.py` script to link any file on your computer directly.

---

## 📁 Project Structure

```
D:\TelegramFileAccessBot\
├── bot.py                  # Main bot application and event loop
├── config.py               # Settings loader from .env
├── database.py             # SQLite database layer for files & active timers
├── utils.py                # Formatting helpers, watermark & keyboard builders
├── register_local_file.py  # Utility to register local files from D: drive
├── .env                    # Environment variables (Bot Token, Admins, etc.)
├── .env.example            # Environment template
├── requirements.txt        # Python dependencies
├── run_bot.bat             # 1-Click launcher batch file
├── bot_database.db         # SQLite database (auto-created on first run)
└── README.md               # Complete documentation
```

---

## 🚀 Quick Setup Guide

### Step 1: Create your Bot Token
1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the prompts to choose a name and username (e.g. `VijayFileAccessBot`).
3. Copy the HTTP API token provided by BotFather (looks like `123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ`).

### Step 2: (Optional) Find your Telegram User ID
1. Search for [@userinfobot](https://t.me/userinfobot) on Telegram and press `/start`.
2. Copy your numeric `Id` (e.g. `123456789`).

### Step 3: Configure `.env`
Open `D:\TelegramFileAccessBot\.env` in any text editor (Notepad, VS Code, etc.) and fill in your values:

```env
BOT_TOKEN=your_actual_bot_token_from_botfather
ADMIN_IDS=your_numeric_telegram_id
DESTRUCT_TIME_SECONDS=300
WATERMARK_TEXT=Made by @VIJAYEDITOR77 on Telegram
WATERMARK_USERNAME=@VIJAYEDITOR77
```

*(If you leave `ADMIN_IDS=` blank, anyone who chats with the bot first can manage files.)*

### Step 4: Run the Bot
Double-click `run_bot.bat` or run via PowerShell:

```powershell
cd D:\TelegramFileAccessBot
python bot.py
```

---

## 💡 How to Use the Bot

### 1. Uploading a File via Telegram
1. Open your bot in Telegram and hit `/start`.
2. As Admin, simply drag & drop or upload any file (video, document, AE project zip, music, image) into the chat.
3. The bot will save the file and reply with:
   - Unique file code (e.g. `x7a9k2b1`)
   - Direct shareable link: `https://t.me/VijayFileAccessBot?start=x7a9k2b1`

### 2. Registering a Local File from D: Drive
You can register any existing video or file from your computer:
```powershell
cd D:\TelegramFileAccessBot
python register_local_file.py "D:\video.mp4"
```

### 3. Delivering & Self-Destruction
1. Send the share link `https://t.me/VijayFileAccessBot?start=<code>` to your client or group.
2. The user taps the link and presses **Start**.
3. The bot instantly sends:
   - **The File** with watermark caption: `Made by @VIJAYEDITOR77 on Telegram`
   - **Urgent Self-Destruct Notice**:
     > 🚨 **CRITICAL SELF-DESTRUCT ALERT** 🚨
     > 🔥 THIS FILE WILL AUTOMATICALLY DESTROY ITSELF IN 5 MINUTES!
     > 📥 QUICKLY SAVE IT IN YOUR SAVED MESSAGES RIGHT NOW before it disappears forever!
4. Exactly **5 minutes (300 seconds)** later, the bot deletes both the file and the warning message from the user's chat.

---

## 🤖 Bot Commands

| Command | Permission | Description |
|---|---|---|
| `/start` | All Users | Start the bot or get the default file |
| `/start <code>` | All Users | Access a specific file via deep-link |
| `/getfile [code]` | All Users | Retrieve file access by code or default |
| `/savedtips` | All Users | Instructions on how to save files to Saved Messages |
| `/listfiles` | Admin | List all registered files, codes, and links |
| `/setdefault <code>` | Admin | Set a file code as the default `/start` file |
| `/delfile <code>` | Admin | Delete a file from the bot registry |
| `/settime <seconds>` | Admin | Adjust self-destruct duration (e.g., `300` for 5 mins) |
| `/status` | Admin | View database stats and active self-destruct countdowns |

---

## 🛡️ Watermark & Attribution
Built specifically with attribution for **@VIJAYEDITOR77 on Telegram**. All notifications, message footers, and direct links include branding back to `https://t.me/VIJAYEDITOR77`.
