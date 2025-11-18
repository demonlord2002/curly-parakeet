import os
import aiohttp
import asyncio
import time
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant, FloodWait
from pymongo import MongoClient
from config import Config

# ---------------- INIT ----------------
app = Client(
    "rin_url_uploader",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# ---------------- MONGO ----------------
mongo = MongoClient(Config.MONGO_URI)
db = mongo["rin_bot"]
users_col = db["users"]

OWNER_IDS = [Config.OWNER_ID]
user_cooldowns = {}
COOLDOWN_TIME = 120
active_tasks = {}

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

# -------- FORCE SUBSCRIBE ----------
async def is_subscribed(user_id: int) -> bool:
    try:
        member = await app.get_chat_member(Config.FORCE_SUB_CHANNEL, user_id)
        return member.status not in ["left", "kicked"]
    except:
        return False

async def send_force_subscribe_prompt(message):
    btn = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚪 Join Channel", url=f"https://t.me/{Config.FORCE_SUB_CHANNEL.replace('@','')}"),
            InlineKeyboardButton("✅ Verify", callback_data="verify_sub")
        ]
    ])
    await message.reply_text(
        "⚡ **Join our Support Channel to unlock access!**",
        reply_markup=btn
    )

# -------- START ----------
@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    user_id = message.from_user.id
    users_col.update_one(
        {"user_id": user_id},
        {"$set": {"first_name": message.from_user.first_name}},
        upsert=True
    )
    if not await is_subscribed(user_id):
        await send_force_subscribe_prompt(message)
        return

    btn = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💜 Owner", url=f"https://t.me/{Config.OWNER_USERNAME}"),
            InlineKeyboardButton("🌸 Support", url=f"https://t.me/{Config.SUPPORT_CHANNEL.replace('@','')}")
        ]
    ])

    await message.reply_photo(
        photo="https://graph.org/file/28a666c9d556b966df561-c11c02a8abe04be820.jpg",
        caption="💜 **Rin's Ninja Uploader** 💜\n\nSend a **Direct Video URL** 💫",
        reply_markup=btn
    )

# -------- VERIFY ----------
@app.on_callback_query(filters.regex("verify_sub"))
async def verify_subscription_cb(client, callback_query):
    if await is_subscribed(callback_query.from_user.id):
        await callback_query.message.edit_text("✅ Verified!")
        await start_cmd(client, callback_query.message)
    else:
        await callback_query.answer("❌ Not subscribed!", show_alert=True)

# -------- TRUE DIRECT DOWNLOADER (XHAMSTER FIX) ---------
async def download_file(url, filepath, status, user_id):
    start_time = time.time()
    downloaded = 0
    chunk_size = 10 * 1024 * 1024
    last_update = 0

    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; Mobile) Chrome/120 Safari/537.36",
        "Referer": url,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(url, allow_redirects=True, ssl=False) as resp:

                if resp.status >= 400:
                    raise Exception(f"HTTP Error {resp.status}")

                total_size = int(resp.headers.get("Content-Length", 0))

                with open(filepath, "wb") as f:
                    async for chunk in resp.content.iter_chunked(chunk_size):
                        if user_id in active_tasks and active_tasks[user_id].cancelled():
                            raise asyncio.CancelledError

                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            if time.time() - last_update > 2:
                                last_update = time.time()
                                text = await progress_bar(downloaded, total_size, start_time, "📥 Downloading")
                                try:
                                    await status.edit_text(text)
                                except:
                                    pass

    except asyncio.CancelledError:
        await status.edit_text("❌ Download cancelled!")
        if os.path.exists(filepath):
            os.remove(filepath)
        raise

# -------- URL HANDLER ----------
@app.on_message(filters.text & ~filters.command(["start", "cancel"]))
async def url_handler(client, message):
    user_id = message.from_user.id

    if not await is_subscribed(user_id):
        await send_force_subscribe_prompt(message)
        return

    url = message.text.strip()

    # Fix filename extraction
    filename = url.split("/")[-1].split("?")[0]
    if "." not in filename:
        filename += ".mp4"

    os.makedirs("downloads", exist_ok=True)
    filepath = f"downloads/{filename}"

    status = await message.reply_text("📥 Starting download...")

    async def task():
        try:
            await download_file(url, filepath, status, user_id)

            await status.edit_text("✅ Download done. Uploading...")

            up_start = time.time()
            last_update = 0

            async def upload_progress(c, t):
                nonlocal last_update
                now = time.time()
                if now - last_update >= 2:
                    last_update = now
                    txt = await progress_bar(c, t, up_start, "📤 Uploading")
                    try: await status.edit_text(txt)
                    except: pass

            await client.send_document(
                message.chat.id,
                filepath,
                file_name=filename,
                progress=upload_progress
            )

            await status.edit_text("✅ Upload completed!")

        except Exception as e:
            await status.edit_text(f"❌ Error: {e}")

        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
            active_tasks.pop(user_id, None)

    active_tasks[user_id] = asyncio.create_task(task())

# -------- CANCEL ----------
@app.on_message(filters.command("cancel"))
async def cancel_handler(client, message):
    task = active_tasks.get(message.from_user.id)
    if task:
        task.cancel()
        await message.reply_text("❌ Download/Upload cancelled!")
    else:
        await message.reply_text("⚠️ No active task!")

# -------- RUN ----------
print("Rin URL Uploader Bot started... 🚀 XHAMSTER FIX ADDED ✅")
app.run()
