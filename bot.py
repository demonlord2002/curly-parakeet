import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from mega import Mega
import config

# Ensure /tmp path exists (Heroku only allows /tmp for writing)
if not os.path.exists(config.TMP_DOWNLOAD_PATH):
    os.makedirs(config.TMP_DOWNLOAD_PATH, exist_ok=True)

# Logging (Heroku logs go to stdout/stderr)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize MEGA sessions
mega_sessions = []
for acc in config.MEGA_ACCOUNTS:
    mega = Mega()
    m = mega.login(acc["email"], acc["password"])
    mega_sessions.append(m)

current_account_idx = 0

def get_next_mega_session():
    global current_account_idx
    return mega_sessions[current_account_idx]

def rotate_mega_account():
    global current_account_idx
    current_account_idx = (current_account_idx + 1) % len(mega_sessions)
    return mega_sessions[current_account_idx]

# ------------------- START COMMAND -------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🤖 Welcome to **File to MEGA Link Bot!**\n\n"
        "Forward or upload any file, and I will generate a permanent MEGA link for you.\n\n"
        "⚡ Only authorized users can use this bot."
    )

    keyboard = [
        [
            InlineKeyboardButton("Owner", url="https://t.me/SunsetOfMe"),
            InlineKeyboardButton("Source Code", url="https://github.com/YourRepoHere"),
            InlineKeyboardButton("Support Channel", url="https://t.me/Fallen_Angels_Team")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")

# ------------------- FILE HANDLER -------------------
async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in config.OWNER_IDS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return

    file_obj = update.message.document or update.message.video or update.message.audio
    if not file_obj:
        await update.message.reply_text("📂 Please forward or upload a file.")
        return

    file_name = file_obj.file_name or "file.bin"

    await update.message.reply_text("⬇️ Downloading file from Telegram...")
    file = await context.bot.get_file(file_obj.file_id)
    local_path = os.path.join(config.TMP_DOWNLOAD_PATH, file_name)
    await file.download_to_drive(local_path)

    max_retries = len(config.MEGA_ACCOUNTS)
    uploaded, link = None, None

    for attempt in range(max_retries):
        session = get_next_mega_session()
        try:
            await update.message.reply_text(f"⬆️ Uploading to MEGA account {attempt + 1}...")
            uploaded = await asyncio.to_thread(session.upload, local_path)
            link = await asyncio.to_thread(session.get_upload_link, uploaded)
            break
        except Exception as e:
            logger.warning(f"Account {attempt+1} failed: {e}. Rotating account...")
            rotate_mega_account()
            continue
    else:
        await update.message.reply_text("❌ All MEGA accounts failed or storage full.")
        try:
            os.remove(local_path)
        except:
            pass
        return

    try:
        os.remove(local_path)
    except:
        pass

    await update.message.reply_text(
        f"✅ File uploaded successfully!\n\n"
        f"📂 Filename: {file_name}\n"
        f"🔗 MEGA Link: {link}"
    )

# ------------------- MAIN -------------------
def main():
    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ALL, handle_file))

    logger.info("🤖 Bot started on Heroku...")
    app.run_polling()

if __name__ == "__main__":
    main()
