import os
import aiohttp
import asyncio
import math
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import Config

# ---------------- INIT ----------------
app = Client(
    "madara_url_uploader",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# -------- PROGRESS BAR ----------
async def progress_bar(current, total, start, stage):
    now = time.time()
    diff = now - start
    percent = current * 100 / total if total != 0 else 0
    speed = current / diff if diff != 0 else 0
    bar_length = 10
    filled = int(bar_length * percent / 100)
    bar = "▓" * filled + "░" * (bar_length - filled)
    eta = (total - current) / speed if speed != 0 else 0
    return f"{stage}:   {bar} {percent:.2f}% | {speed/1024/1024:.2f} MB/s | ETA: {int(eta)}s"

# -------- START CMD ----------
@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Support Channel", url=Config.SUPPORT_CHANNEL)],
        [InlineKeyboardButton("👤 Owner", url=f"https://t.me/{Config.OWNER_USERNAME}")]
    ])
    await message.reply_text(
        "**🔥 𝙈𝘼𝘿𝘼𝙍𝘼 𝙐𝙍𝙇 𝙐𝙋𝙇𝙊𝘼𝘿𝙀𝙍 🔥**\n\n"
        "➤ Send me any **Direct Video URL** (mp4/mkv).\n"
        "➤ I will **download + upload** it to Telegram.\n"
        "➤ Only **.mp4 / .mkv** are accepted ⚡\n\n"
        "**⚡ Speed Beast Mode Activated ⚡**",
        reply_markup=btn
    )

# -------- URL HANDLER ----------
@app.on_message(filters.text & ~filters.command(["start"]))
async def url_handler(client, message):
    url = message.text.strip()

    # Guess filename
    filename = url.split("/")[-1].split("?")[0]
    ext = os.path.splitext(filename)[-1].lower()

    if ext not in Config.ALLOWED_EXTENSIONS:
        filename = filename + ".mkv"
        ext = ".mkv"

    filepath = os.path.join("downloads", filename)
    os.makedirs("downloads", exist_ok=True)

    status = await message.reply_text("📥 Starting download...")

    # -------- DOWNLOAD --------
    try:
        start_time = time.time()
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                total_size = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                with open(filepath, "wb") as f:
                    async for chunk in resp.content.iter_chunked(1024 * 1024):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if time.time() - start_time > 2:
                                text = await progress_bar(downloaded, total_size, start_time, "📥 Downloading")
                                await status.edit_text(text)
                                start_time = time.time()

        await status.edit_text("✅ Download completed. Starting upload...")

        # -------- UPLOAD --------
        up_start = time.time()
        async def upload_progress(current, total):
            text = await progress_bar(current, total, up_start, "📤 Uploading")
            try:
                await status.edit_text(text)
            except:
                pass

        await client.send_document(
            chat_id=message.chat.id,
            document=filepath,
            file_name=filename,
            progress=upload_progress
        )
        await status.edit_text("✅ Upload completed!")

    except Exception as e:
        await status.edit_text(f"❌ Error: {e}")

    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

# ---------------- RUN ----------------
print("Madara URL Uploader Bot started...")
app.run()
