import os
import aiohttp
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant, FloodWait
from pymongo import MongoClient
from config import Config

# ---------------- INIT ----------------
app = Client(
    "madara_url_uploader",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# ---------------- MONGO ----------------
mongo = MongoClient(Config.MONGO_URI)
db = mongo["madara_bot"]
users_col = db["users"]

# ---------------- OWNER ----------------
OWNER_IDS = [Config.OWNER_ID]

# -------- PROGRESS BAR ----------
async def progress_bar(current, total, start, stage):
    now = time.time()
    diff = now - start
    percent = current * 100 / total if total else 0
    speed = current / diff if diff else 0
    bar_length = 12
    filled = int(bar_length * percent / 100)
    bar = "▓" * filled + "░" * (bar_length - filled)
    eta = (total - current) / speed if speed else 0
    return f"{stage}: {bar} {percent:.2f}% | {speed/1024/1024:.2f} MB/s | ETA: {int(eta)}s"

# -------- FORCE SUBSCRIBE CHECK ----------
async def is_subscribed(user_id: int) -> bool:
    try:
        member = await app.get_chat_member(Config.FORCE_SUB_CHANNEL, user_id)
        return member.status not in ["left", "kicked"]
    except UserNotParticipant:
        return False
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await is_subscribed(user_id)
    except Exception as e:
        print(f"[is_subscribed] Error: {e}")
        return False

# -------- FORCE SUBSCRIBE PROMPT ----------
async def send_force_subscribe_prompt(message):
    btn = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚪 Join Channel", url=f"https://t.me/{Config.FORCE_SUB_CHANNEL.replace('@','')}"),
            InlineKeyboardButton("✅ Verify", callback_data="verify_sub")
        ]
    ])
    await message.reply_text(
        "⚡ **Join our Support Channel to unlock access!** ⚡\n🔒 Access locked until you join ❤️🥷",
        reply_markup=btn
    )

# -------- START CMD ----------
@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    user_id = message.from_user.id
    users_col.update_one(
        {"user_id": user_id},
        {"$set": {"first_name": message.from_user.first_name, "username": message.from_user.username}},
        upsert=True
    )

    if not await is_subscribed(user_id):
        await send_force_subscribe_prompt(message)
        return

    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Support Channel", url=f"https://t.me/{Config.SUPPORT_CHANNEL.replace('@','')}")],
        [InlineKeyboardButton("👤 Owner", url=f"https://t.me/{Config.OWNER_USERNAME}")]
    ])
    await message.reply_text(
        f"**🔥 MADARA URL UPLOADER 🔥**\n\n👋 Hello **{message.from_user.first_name}**!\n"
        "➤ Send any **Direct Video URL** (.mp4/.mkv)\n"
        "➤ I will **download + upload** it at ⚡ high speed ⚡\n"
        "**⚡ Speed Beast Mode Activated ⚡**",
        reply_markup=btn
    )

# -------- VERIFY CALLBACK ----------
@app.on_callback_query(filters.regex("verify_sub"))
async def verify_subscription_cb(client, callback_query):
    if await is_subscribed(callback_query.from_user.id):
        await callback_query.message.edit_text("✅ Verified! Welcome to Madara Family ❤️")
        await start_cmd(client, callback_query.message)
    else:
        await callback_query.answer("❌ Not subscribed yet! Join first ⚡", show_alert=True)

# -------- FAST MULTI-CHUNK DOWNLOAD ----------
async def download_file(url, filepath, status):
    """
    High-speed multi-chunk downloader (~10MB/s if server allows)
    """
    start_time = time.time()
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=50)) as session:
        async with session.head(url) as head_resp:
            total_size = int(head_resp.headers.get("Content-Length", 0))
        chunk_size = 4 * 1024 * 1024  # 4MB per chunk
        chunks = [(i, min(i + chunk_size - 1, total_size - 1)) for i in range(0, total_size, chunk_size)]
        downloaded_data = [None] * len(chunks)
        last_update = start_time

        async def download_chunk(idx, start, end):
            nonlocal last_update
            headers = {"Range": f"bytes={start}-{end}"}
            async with session.get(url, headers=headers) as resp:
                downloaded_data[idx] = await resp.read()
                downloaded_bytes = sum(len(c) for c in downloaded_data if c)
                if time.time() - last_update > 0.5:
                    text = await progress_bar(downloaded_bytes, total_size, start_time, "📥 Downloading")
                    try: await status.edit_text(text)
                    except: pass
                    last_update = time.time()

        await asyncio.gather(*[download_chunk(i, s, e) for i, (s, e) in enumerate(chunks)])

        with open(filepath, "wb") as f:
            for chunk in downloaded_data:
                f.write(chunk)

# -------- URL HANDLER ----------
@app.on_message(filters.text & ~filters.command(["start"]))
async def url_handler(client, message):
    user_id = message.from_user.id
    if not await is_subscribed(user_id):
        await send_force_subscribe_prompt(message)
        return

    url = message.text.strip()
    filename = url.split("/")[-1].split("?")[0]
    if not any(filename.endswith(ext) for ext in Config.ALLOWED_EXTENSIONS):
        filename += ".mkv"

    os.makedirs("downloads", exist_ok=True)
    filepath = os.path.join("downloads", filename)
    status = await message.reply_text("📥 Starting download...")

    try:
        await download_file(url, filepath, status)
        await status.edit_text("✅ Download completed. Starting upload...")

        up_start = time.time()
        last_update = 0

        async def upload_progress(current, total):
            nonlocal last_update
            now = time.time()
            if now - last_update >= 1 or current == total:
                last_update = now
                text = await progress_bar(current, total, up_start, "📤 Uploading")
                try: await status.edit_text(text)
                except: pass

        await client.send_document(
            chat_id=message.chat.id,
            document=filepath,
            file_name=filename,
            progress=upload_progress
        )
        await status.edit_text("✅ Upload completed! 🔥")

    except Exception as e:
        await status.edit_text(f"❌ Error: {e}")
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

# ---------------- RUN ----------------
print("Madara URL Uploader Bot started... 🚀 High-Speed Mode ✅")
app.run()
