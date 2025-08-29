import os
import time
import logging
import threading
from datetime import datetime

from flask import Flask, redirect, abort
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient, ReturnDocument

import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB Setup
mongo = MongoClient(config.MONGO_URI)
db = mongo["file_share_bot"]
files_col = db["files"]
counters_col = db["counters"]

# Generate incremental file_id
def next_file_id():
    doc = counters_col.find_one_and_update(
        {"_id": "fileid"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(doc["seq"])

# Pyrogram Client
app = Client(
    "file_share_bot",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
)

# Flask App
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "🚀 File Share Bot is running!"

@flask_app.route("/d/<int:file_id>")
def direct_download(file_id):
    file_doc = files_col.find_one({"file_id": file_id, "status": "active"})
    if not file_doc:
        return abort(404, "File not found")

    try:
        # Get a direct download URL from Telegram
        tg_file = app.get_messages(file_doc["uploader_id"], file_doc["tg_file_id"])
        file_path = app.get_file(file_doc["tg_file_id"])
        file_url = f"https://api.telegram.org/file/bot{config.BOT_TOKEN}/{file_path.file_path}"
        return redirect(file_url)
    except Exception as e:
        logger.exception("Direct download failed")
        return abort(500, "Download failed")

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    flask_app.run(host="0.0.0.0", port=port)

# Build share link (browser download link)
def build_share_link(file_id_int: int) -> str:
    heroku_url = os.environ.get("HEROKU_APP_URL", "").rstrip("/")
    if not heroku_url:
        return f"https://t.me/{config.BOT_USERNAME}?start=file_{file_id_int}"  # fallback
    return f"{heroku_url}/d/{file_id_int}"

# /start
@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message):
    await message.reply_text("👋 Send me a file, I'll give you a direct download link!")

# Save files
@app.on_message(filters.private & (filters.document | filters.video | filters.photo))
async def save_file(client, message):
    tg_file_id, ftype, fname, fsize = None, "document", None, 0

    if message.document:
        tg_file_id = message.document.file_id
        fname = message.document.file_name
        fsize = message.document.file_size
        ftype = "document"
    elif message.video:
        tg_file_id = message.video.file_id
        fname = message.video.file_name or f"video_{int(time.time())}.mp4"
        fsize = message.video.file_size
        ftype = "video"
    elif message.photo:
        tg_file_id = message.photo.file_id
        fname = f"photo_{int(time.time())}.jpg"
        ftype = "photo"

    if not tg_file_id:
        await message.reply_text("❌ Unsupported file type.")
        return

    if fsize and fsize > config.MAX_FILE_SIZE_MB * 1024 * 1024:
        await message.reply_text(f"⚠️ File too large. Max {config.MAX_FILE_SIZE_MB} MB allowed.")
        return

    file_id_int = next_file_id()
    doc = {
        "file_id": file_id_int,
        "tg_file_id": tg_file_id,
        "uploader_id": message.from_user.id,
        "name": fname,
        "size": fsize,
        "type": ftype,
        "status": "active",
        "uploaded_at": datetime.utcnow(),
    }
    files_col.insert_one(doc)

    share_link = build_share_link(file_id_int)
    await message.reply_text(
        f"✅ File saved!\n\n📂 ID: `{file_id_int}`\n🔗 Direct Link: {share_link}"
    )

if __name__ == "__main__":
    # Run Flask in a separate thread
    threading.Thread(target=run_flask).start()
    app.run()
