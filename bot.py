import os
import sys
import time
import logging
import asyncio
from pathlib import Path
from typing import Optional, List

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.error import TelegramError

from config import (
    BOT_TOKEN,
    ADMIN_IDS,
    DESTRUCT_TIME_SECONDS,
    WATERMARK_TEXT,
    WATERMARK_USERNAME,
    FILES_DIR,
)
import database
import utils

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("FileAccessBot")

def is_admin(user_id: int) -> bool:
    """Check if user is admin. If no admins configured, allow first user or notify."""
    if not ADMIN_IDS:
        return True
    return user_id in ADMIN_IDS

def get_current_destruct_time() -> int:
    """Retrieve configured destruction time from DB or config."""
    db_time = database.get_setting("destruct_time")
    if db_time and db_time.isdigit():
        return int(db_time)
    return DESTRUCT_TIME_SECONDS

async def schedule_self_destruction(
    bot,
    chat_id: int,
    file_msg_id: int,
    warn_msg_id: int,
    file_code: str,
    duration: int,
    share_id: Optional[int] = None
):
    """Wait for duration, delete the file and warning message, then notify user."""
    expires_at = time.time() + duration
    if share_id is None:
        share_id = database.record_active_share(
            chat_id=chat_id,
            file_message_id=file_msg_id,
            warning_message_id=warn_msg_id,
            file_code=file_code,
            expires_at=expires_at
        )

    # Sleep until expiration
    remaining = max(0.0, expires_at - time.time())
    await asyncio.sleep(remaining)

    # Delete the file message
    try:
        await bot.delete_message(chat_id=chat_id, message_id=file_msg_id)
        logger.info(f"Deleted file message {file_msg_id} in chat {chat_id}")
    except TelegramError as e:
        logger.warning(f"Failed to delete file message {file_msg_id} in {chat_id}: {e}")

    # Delete the warning message
    try:
        await bot.delete_message(chat_id=chat_id, message_id=warn_msg_id)
        logger.info(f"Deleted warning message {warn_msg_id} in chat {chat_id}")
    except TelegramError as e:
        logger.warning(f"Failed to delete warning message {warn_msg_id} in {chat_id}: {e}")

    # Mark as deleted in DB
    if share_id:
        database.mark_share_deleted(share_id)

    # Send final expiration notice
    try:
        clean_user = WATERMARK_USERNAME.lstrip("@")
        expired_msg = await bot.send_message(
            chat_id=chat_id,
            text=(
                "💥 *TIME'S UP! THE FILE HAS SELF-DESTRUCTED!* 💥\n\n"
                "⏱️ The 5-minute access window has officially expired.\n"
                "📁 The file and security messages have been permanently deleted from this chat.\n\n"
                "✅ *Did you save it in your Saved Messages?* If yes, your copy is safe!\n"
                "❌ If you missed it, request a fresh link.\n"
                f"{utils.get_watermark_footer()}"
            ),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f"⚡ {WATERMARK_TEXT}", url=f"https://t.me/{clean_user}")]
            ])
        )
        # Auto-delete the expiration notification after 60 seconds to keep chat clean
        await asyncio.sleep(60)
        try:
            await bot.delete_message(chat_id=chat_id, message_id=expired_msg.message_id)
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Failed to send expiration notification to {chat_id}: {e}")

async def deliver_file_to_chat(
    bot,
    chat_id: int,
    file_record: dict,
    destruct_time: int
) -> bool:
    """Deliver a file and trigger self-destruction countdown."""
    file_type = file_record.get("file_type", "document")
    file_id = file_record.get("file_id")
    local_path = file_record.get("local_path")
    file_name = file_record.get("file_name") or "File"
    file_size = file_record.get("file_size") or 0
    file_code = file_record.get("file_code", "")

    caption = utils.build_file_caption(file_name, file_size)

    file_obj = file_id
    if not file_obj and local_path and os.path.exists(local_path):
        try:
            file_obj = open(local_path, "rb")
        except Exception as e:
            logger.error(f"Failed to open local file {local_path}: {e}")
            return False

    if not file_obj:
        return False

    file_msg = None
    try:
        if file_type == "video":
            file_msg = await bot.send_video(chat_id=chat_id, video=file_obj, caption=caption, parse_mode="Markdown")
        elif file_type == "photo":
            file_msg = await bot.send_photo(chat_id=chat_id, photo=file_obj, caption=caption, parse_mode="Markdown")
        elif file_type == "audio":
            file_msg = await bot.send_audio(chat_id=chat_id, audio=file_obj, caption=caption, parse_mode="Markdown")
        else:
            file_msg = await bot.send_document(
                chat_id=chat_id,
                document=file_obj,
                filename=file_name,
                caption=caption,
                parse_mode="Markdown"
            )
    except TelegramError as te:
        logger.warning(f"Failed to send with Markdown caption: {te}. Retrying with plain text...")
        if hasattr(file_obj, "seek"):
            file_obj.seek(0)
        plain_caption = caption.replace("*", "").replace("`", "")
        try:
            if file_type == "video":
                file_msg = await bot.send_video(chat_id=chat_id, video=file_obj, caption=plain_caption)
            elif file_type == "photo":
                file_msg = await bot.send_photo(chat_id=chat_id, photo=file_obj, caption=plain_caption)
            elif file_type == "audio":
                file_msg = await bot.send_audio(chat_id=chat_id, audio=file_obj, caption=plain_caption)
            else:
                file_msg = await bot.send_document(
                    chat_id=chat_id,
                    document=file_obj,
                    filename=file_name,
                    caption=plain_caption
                )
        except Exception as retry_err:
            logger.error(f"Retry send also failed: {retry_err}")
            return False
    finally:
        if hasattr(file_obj, "close"):
            file_obj.close()

    if not file_msg:
        return False

    # Cache file_id for faster subsequent deliveries
    if not file_record.get("file_id"):
        new_fid = None
        if file_msg.document:
            new_fid = file_msg.document.file_id
        elif file_msg.video:
            new_fid = file_msg.video.file_id
        elif file_msg.photo:
            new_fid = file_msg.photo[-1].file_id
        elif file_msg.audio:
            new_fid = file_msg.audio.file_id

        if new_fid and file_code:
            database.update_file_id(file_code, new_fid)

    # If destruct_time is configured, schedule self-destruction
    if destruct_time > 0:
        warning_text = utils.build_destruct_warning_text(destruct_time)
        keyboard = utils.get_file_delivery_keyboard(file_code)
        try:
            warn_msg = await bot.send_message(
                chat_id=chat_id,
                text=warning_text,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
        except TelegramError:
            warn_msg = await bot.send_message(
                chat_id=chat_id,
                text=warning_text.replace("*", ""),
                reply_markup=keyboard
            )

        # Launch asynchronous self-destruct countdown
        asyncio.create_task(
            schedule_self_destruction(
                bot=bot,
                chat_id=chat_id,
                file_msg_id=file_msg.message_id,
                warn_msg_id=warn_msg.message_id,
                file_code=file_code,
                duration=destruct_time
            )
        )
    return True

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with or without deep linking."""
    if not update.effective_chat or not update.effective_user:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    destruct_time = get_current_destruct_time()

    # Check for deep-link parameter: /start <code>
    if context.args and len(context.args) > 0:
        requested_code = context.args[0].strip()
        file_record = database.get_file(requested_code)
        if file_record:
            success = await deliver_file_to_chat(context.bot, chat_id, file_record, destruct_time)
            if not success:
                await update.message.reply_text("⚠️ Could not load the requested file. Please contact administrator.")
            return

    # No deep-link argument provided or code not matching: deliver default file
    default_file = database.get_default_file()
    if default_file:
        timer_msg = f"⏳ Self-destruction timer of {destruct_time // 60} minutes will start upon delivery!\n" if destruct_time > 0 else ""
        await update.message.reply_text(
            "⚡ *Delivering Primary Access File...*\n"
            f"{timer_msg}"
            f"{utils.get_watermark_footer()}",
            parse_mode="Markdown"
        )
        await deliver_file_to_chat(context.bot, chat_id, default_file, destruct_time)
        return

    # Welcome message when no files or parameters exist
    clean_user = WATERMARK_USERNAME.lstrip("@")
    welcome_text = (
        f"👋 *Welcome to File Access Bot!*\n\n"
        f"🔐 Use your designated access link to download exclusive files.\n\n"
        f"⚠️ *Important Self-Destruct Notice:*\n"
        f"• All delivered files *self-destruct in 5 minutes*.\n"
        f"• Be sure to forward/save files to your *Saved Messages* immediately!\n"
        f"{utils.get_watermark_footer()}"
    )

    if is_admin(user_id):
        welcome_text += (
            "\n\n👑 *Admin Controls Quick Start:*\n"
            "• Forward or send any file directly here to generate an access link.\n"
            "• `/listfiles` - View all saved files & links\n"
            "• `/setdefault <code>` - Set default file for `/start`\n"
            "• `/settime <seconds>` - Change self-destruct timer\n"
            "• `/status` - Bot database status"
        )

    keyboard = [
        [InlineKeyboardButton("💡 How to Save to Saved Messages", callback_data="saved_guide")],
        [InlineKeyboardButton(f"⚡ {WATERMARK_TEXT}", url=f"https://t.me/{clean_user}")]
    ]
    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def getfile_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /getfile [code] command."""
    chat_id = update.effective_chat.id
    destruct_time = get_current_destruct_time()

    if context.args and len(context.args) > 0:
        requested_code = context.args[0].strip()
        file_record = database.get_file(requested_code)
    else:
        file_record = database.get_default_file()

    if not file_record:
        await update.message.reply_text(
            "❌ No file available with that code, and no default file is set.\n"
            f"{utils.get_watermark_footer()}",
            parse_mode="Markdown"
        )
        return

    await deliver_file_to_chat(context.bot, chat_id, file_record, destruct_time)

async def handle_incoming_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle files uploaded by admin/owner to create share links."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text(
            "⛔ You do not have permission to upload files to this bot.\n"
            f"{utils.get_watermark_footer()}",
            parse_mode="Markdown"
        )
        return

    msg = update.message
    file_id = None
    file_name = "Untitled"
    file_size = 0
    file_type = "document"

    if msg.document:
        file_id = msg.document.file_id
        file_name = msg.document.file_name or "document.bin"
        file_size = msg.document.file_size or 0
        file_type = "document"
    elif msg.video:
        file_id = msg.video.file_id
        file_name = msg.video.file_name or "video.mp4"
        file_size = msg.video.file_size or 0
        file_type = "video"
    elif msg.audio:
        file_id = msg.audio.file_id
        file_name = msg.audio.file_name or "audio.mp3"
        file_size = msg.audio.file_size or 0
        file_type = "audio"
    elif msg.photo:
        file_id = msg.photo[-1].file_id
        file_name = f"photo_{int(time.time())}.jpg"
        file_size = msg.photo[-1].file_size or 0
        file_type = "photo"

    if not file_id:
        await update.message.reply_text("Could not process this file format.")
        return

    file_code = utils.generate_file_code(8)
    
    # Check if there is already a default file; if not, make this the default
    is_default = 1 if not database.get_default_file() else 0
    database.add_file(
        file_code=file_code,
        file_id=file_id,
        file_type=file_type,
        file_name=file_name,
        file_size=file_size,
        is_default=is_default
    )

    bot_info = await context.bot.get_me()
    bot_username = bot_info.username or "YourBot"
    share_link = f"https://t.me/{bot_username}?start={file_code}"
    timer_mins = get_current_destruct_time() // 60

    response_text = (
        f"✅ *FILE REGISTERED SUCCESSFULLY!*\n\n"
        f"📂 *Name:* `{file_name}`\n"
        f"📊 *Size:* `{utils.format_file_size(file_size)}`\n"
        f"🏷️ *Type:* `{file_type.capitalize()}`\n"
        f"🔑 *Code:* `{file_code}`\n"
        f"⭐ *Default File:* `{'Yes' if is_default else 'No'}`\n\n"
        f"🔗 *Shareable Access Link:*\n`{share_link}`\n\n"
        f"⚠️ When a user clicks this link, the file will be sent with a *{timer_mins}-minute self-destruct timer*!\n"
        f"{utils.get_watermark_footer()}"
    )

    keyboard = utils.get_admin_keyboard(file_code, bot_username)
    await update.message.reply_text(
        response_text,
        parse_mode="Markdown",
        reply_markup=keyboard
    )

async def list_files_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all saved files (Admin only)."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    files = database.list_files()
    if not files:
        await update.message.reply_text("📂 No files registered yet. Send any file to add one!")
        return

    bot_info = await context.bot.get_me()
    bot_username = bot_info.username or "YourBot"

    text = "📂 *REGISTERED FILES:*\n\n"
    for idx, f in enumerate(files, 1):
        def_tag = " ⭐ [DEFAULT]" if f["is_default"] else ""
        size_str = utils.format_file_size(f["file_size"])
        link = f"https://t.me/{bot_username}?start={f['file_code']}"
        text += (
            f"*{idx}. {f['file_name']}*{def_tag}\n"
            f"   • Code: `{f['file_code']}` | Size: `{size_str}`\n"
            f"   • Link: `{link}`\n\n"
        )

    text += f"{utils.get_watermark_footer()}"
    await update.message.reply_text(text, parse_mode="Markdown", disable_web_page_preview=True)

async def set_default_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set default file: /setdefault <code> (Admin only)."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    if not context.args:
        await update.message.reply_text("Usage: `/setdefault <file_code>`", parse_mode="Markdown")
        return

    code = context.args[0].strip()
    if database.set_default_file(code):
        await update.message.reply_text(f"⭐ File `{code}` set as the default file!", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ File code `{code}` not found.", parse_mode="Markdown")

async def delete_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a file: /delfile <code> (Admin only)."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    if not context.args:
        await update.message.reply_text("Usage: `/delfile <file_code>`", parse_mode="Markdown")
        return

    code = context.args[0].strip()
    if database.delete_file(code):
        await update.message.reply_text(f"🗑️ File `{code}` deleted successfully.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ File code `{code}` not found.", parse_mode="Markdown")

async def set_time_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set destruction timer in seconds: /settime <seconds> (Admin only)."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "Usage: `/settime <seconds>` (e.g., `/settime 300` for 5 minutes)",
            parse_mode="Markdown"
        )
        return

    seconds = int(context.args[0])
    if seconds < 10 or seconds > 86400:
        await update.message.reply_text("Please specify a duration between 10 seconds and 86400 seconds (24h).")
        return

    database.set_setting("destruct_time", str(seconds))
    mins = seconds / 60
    await update.message.reply_text(
        f"⏱️ Self-destruct timer updated to *{seconds} seconds* ({mins:.1f} minutes)!\n"
        f"{utils.get_watermark_footer()}",
        parse_mode="Markdown"
    )

async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View bot status (Admin only)."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    files = database.list_files()
    pending = database.get_pending_active_shares()
    timer = get_current_destruct_time()

    status_text = (
        f"🤖 *BOT STATUS & DIAGNOSTICS:*\n\n"
        f"📁 Total Files: `{len(files)}`\n"
        f"⏳ Self-Destruct Timer: `{timer}s` ({timer // 60}m)\n"
        f"🔥 Active Self-Destructs Counting Down: `{len(pending)}`\n"
        f"🛡️ Watermark: `{WATERMARK_TEXT}`\n"
        f"👤 Channel: `{WATERMARK_USERNAME}`\n"
        f"{utils.get_watermark_footer()}"
    )
    await update.message.reply_text(status_text, parse_mode="Markdown")

async def saved_guide_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show guide on saving files to Saved Messages."""
    text = (
        "📥 *HOW TO SAVE FILES TO 'SAVED MESSAGES':*\n\n"
        "To prevent losing files when the 5-minute timer destroys them:\n\n"
        "📱 *On Android / iPhone:*\n"
        "1. Press & hold the file message until selected.\n"
        "2. Tap the *Forward* arrow button.\n"
        "3. Choose *Saved Messages* from your chat list.\n"
        "4. Hit *Send*! Your file is now safely stored in your cloud storage!\n\n"
        "💻 *On Telegram Desktop / Mac / Web:*\n"
        "1. Right-click on the file message.\n"
        "2. Click *Forward Message*.\n"
        "3. Select *Saved Messages*.\n"
        "4. Click *Send*!\n\n"
        "💡 *Tip:* You can also click the 3 dots '...' on any file and click *'Save to Downloads'*.\n"
        f"{utils.get_watermark_footer()}"
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button clicks."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "saved_guide":
        await saved_guide_handler(update, context)
    elif data.startswith("set_def_"):
        code = data.replace("set_def_", "")
        database.set_default_file(code)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"⭐ File `{code}` set as default file!", parse_mode="Markdown")
    elif data.startswith("del_"):
        code = data.replace("del_", "")
        database.delete_file(code)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"🗑️ File `{code}` deleted.", parse_mode="Markdown")

async def resume_pending_timers(application: Application):
    """Resume any pending countdowns after bot restart."""
    pending = database.get_pending_active_shares()
    now = time.time()
    for item in pending:
        share_id = item["id"]
        chat_id = item["chat_id"]
        f_msg_id = item["file_message_id"]
        w_msg_id = item["warning_message_id"]
        f_code = item["file_code"]
        expires_at = item["expires_at"]

        remaining = int(expires_at - now)
        if remaining <= 0:
            # Expired while bot was offline; delete immediately
            asyncio.create_task(
                schedule_self_destruction(
                    bot=application.bot,
                    chat_id=chat_id,
                    file_msg_id=f_msg_id,
                    warn_msg_id=w_msg_id,
                    file_code=f_code,
                    duration=0,
                    share_id=share_id
                )
            )
        else:
            # Resume countdown
            asyncio.create_task(
                schedule_self_destruction(
                    bot=application.bot,
                    chat_id=chat_id,
                    file_msg_id=f_msg_id,
                    warn_msg_id=w_msg_id,
                    file_code=f_code,
                    duration=remaining,
                    share_id=share_id
                )
            )

async def post_init(application: Application):
    """Actions performed once the bot connects."""
    database.init_db()
    # Explicitly purge any old Axkush files from the database
    try:
        with database.get_connection() as conn:
            conn.execute("DELETE FROM files WHERE file_name LIKE '%Axkush%'")
            conn.commit()
    except Exception as e:
        logger.warning(f"Cleanup notice: {e}")

    # Always ensure files directory is scanned and Cavalca_Main_CC.ffx is registered as default
    if FILES_DIR.exists():
        cavalca = FILES_DIR / "Cavalca_Main_CC.ffx"
        if cavalca.exists():
            import register_local_file
            register_local_file.register_file(str(cavalca), is_default=True)
        elif not database.get_default_file():
            for candidate in sorted(FILES_DIR.iterdir()):
                if candidate.is_file():
                    import register_local_file
                    register_local_file.register_file(str(candidate), is_default=True)
                    break
    await resume_pending_timers(application)
    bot_info = await application.bot.get_me()
    logger.info(f"Bot started successfully as @{bot_info.username}")
    print(f"=====================================================")
    print(f"🚀 Bot is running: @{bot_info.username}")
    print(f"🛡️ Watermark: {WATERMARK_TEXT}")
    print(f"⏱️ Self-Destruct Timer: {get_current_destruct_time()} seconds (5 minutes)")
    print(f"=====================================================")

def main():
    """Main entrypoint."""
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("\n" + "!" * 60)
        print("ERROR: BOT_TOKEN is not configured in .env file!")
        print("Please edit D:\\TelegramFileAccessBot\\.env and set your BOT_TOKEN.")
        print("Get a token from @BotFather on Telegram.")
        print("!" * 60 + "\n")
        sys.exit(1)

    import keep_alive
    keep_alive.start_health_server()

    database.init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    # Commands
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("getfile", getfile_handler))
    app.add_handler(CommandHandler("listfiles", list_files_handler))
    app.add_handler(CommandHandler("setdefault", set_default_handler))
    app.add_handler(CommandHandler("delfile", delete_file_handler))
    app.add_handler(CommandHandler("settime", set_time_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("savedtips", saved_guide_handler))
    app.add_handler(CommandHandler("help", start_handler))

    # Media uploads
    media_filter = (
        filters.Document.ALL |
        filters.VIDEO |
        filters.AUDIO |
        filters.PHOTO
    )
    app.add_handler(MessageHandler(media_filter, handle_incoming_file))

    # Inline callbacks
    app.add_handler(CallbackQueryHandler(button_callback_handler))

    # Start polling
    logger.info("Starting Telegram Bot Polling...")
    app.run_polling()

if __name__ == "__main__":
    main()
