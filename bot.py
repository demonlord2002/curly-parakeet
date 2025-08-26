import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from mega import Mega
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize all MEGA sessions
mega_sessions = []
for acc in config.MEGA_ACCOUNTS:
    mega = Mega()
    m = mega.login(acc["email"], acc["password"])
    mega_sessions.append(m)

# Index of current active account
current_account_idx = 0

def get_next_mega_session():
    """Return the current MEGA session; rotate if needed"""
    global current_account_idx
    session = mega_sessions[current_account_idx]
    return session

def rotate_mega_account():
    """Switch to the next MEGA account"""
    global current_account_idx
    current_account_idx += 1
    if current_account_idx >= len(mega_sessions):
        current_account_idx = 0  # loop back to first
    return mega_sessions[current_account_idx]

# ------------------- START COMMAND -------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = (
        "🤖 Welcome to **File to MEGA Link Bot!**\n\n"
        "Forward or upload any file, and I will generate a permanent MEGA link for you.\n\n"
        "⚡ Only authorized users can use this bot."
    )

    # Inline button layout: Owner (left), Source Code (center), Support (right)
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

    if not update.message.document and not update.message.video and not update.message.audio:
        await update.message.reply_text("📂 Please forward or upload a file.")
        return

    file_obj = update.message.document or update.message.video or update.message.audio
    file_name = file_obj.file_name or "file.bin"

    # Download file
    await update.message.reply_text("⬇️ Downloading file from Telegram...")
    file = await context.bot.get_file(file_obj.file_id)
    local_path = os.path.join(config.TMP_DOWNLOAD_PATH, file_name)
    await file.download_to_drive(local_path)

    # Upload to MEGA with account rotation
    max_retries = len(config.MEGA_ACCOUNTS)
    uploaded = None
    for attempt in range(max_retries):
        session = get_next_mega_session()
        try:
            await update.message.reply_text(f"⬆️ Uploading to MEGA account {attempt + 1}...")
            uploaded = session.upload(local_path)
            link = session.get_upload_link(uploaded)
            break  # success
        except Exception as e:
            logger.warning(f"Account {attempt+1} failed: {e}. Rotating to next account...")
            session = rotate_mega_account()
            continue
    else:
        await update.message.reply_text("❌ All MEGA accounts failed or full storage.")
        try:
            os.remove(local_path)
        except:
            pass
        return

    # Cleanup local file
    try:
        os.remove(local_path)
    except:
        pass

    # Reply with permanent MEGA link
    await update.message.reply_text(
        f"✅ File uploaded successfully!\n\n"
        f"📂 Filename: {file_name}\n"
        f"🔗 MEGA Link: {link}"
    )

# ------------------- MAIN -------------------
def main():
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    # /start command
    app.add_handler(CommandHandler("start", start))
    
    # Handle all file messages
    app.add_handler(MessageHandler(filters.ALL, handle_file))

    print("🤖 Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
