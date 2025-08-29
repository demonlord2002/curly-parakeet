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
    percent = current * 100 / total if total != 0 else 0
    speed = current / diff if diff != 0 else 0
    bar_length = 12
    filled = int(bar_length * percent / 100)
    bar = "▓" * filled + "░" * (bar_length - filled)
    eta = (total - current) / speed if speed != 0 else 0
    return f"{stage}:   {bar} {percent:.2f}% | {speed/1024/1024:.2f} MB/s | ETA: {int(eta)}s"

# -------- FORCE SUBSCRIBE CHECK ----------
async def is_subscribed(user_id):
    try:
        channel = Config.SUPPORT_CHANNEL
        if isinstance(channel, str) and not str(channel).startswith("@"):
            channel = "@" + str(channel)
        member = await app.get_chat_member(channel, user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
    except UserNotParticipant:
        return False
    except Exception as e:
        print(f"Subscription check error: {e}")
        return False
    return False

# -------- FORCE SUBSCRIBE PROMPT ----------
async def send_force_subscribe_prompt(message):
    channel = Config.SUPPORT_CHANNEL
    if not str(channel).startswith("@"):
        channel = "@" + str(channel)
    btn = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚪 Join Now", url=f"https://t.me/{channel}"),
            InlineKeyboardButton("✅ Verified", callback_data="verify_sub")
        ]
    ])
    await message.reply_text(
        "**⚠️ Attention!**\n\n"
        "You must join our official support channel to use this bot.\n\n"
        "Press 🚪 Join Now to join, then click ✅ Verified to continue.",
        reply_markup=btn
    )

# -------- START CMD ----------
@app.on_message(filters.command("start"))
async def start_cmd(client, message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    username = message.from_user.username

    users_col.update_one(
        {"user_id": user_id},
        {"$set": {"first_name": first_name, "username": username}},
        upsert=True
    )

    if not await is_subscribed(user_id):
        await send_force_subscribe_prompt(message)
        return

    btn = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Support Channel", url=f"https://t.me/{Config.SUPPORT_CHANNEL}")],
        [InlineKeyboardButton("👤 Owner", url=f"https://t.me/{Config.OWNER_USERNAME}")]
    ])
    await message.reply_text(
        f"**🔥 MADARA URL UPLOADER 🔥**\n\n"
        f"👋 Hello **{first_name}**!\n"
        "➤ Send me any **Direct Video URL** (.mp4/.mkv)\n"
        "➤ I will **download + upload** it at ⚡ high speed ⚡\n"
        "➤ Only **.mp4 / .mkv** are accepted\n\n"
        "**⚡ Speed Beast Mode Activated ⚡**",
        reply_markup=btn
    )

# -------- CALLBACK QUERY FOR VERIFIED BUTTON ----------
@app.on_callback_query(filters.regex("verify_sub"))
async def verify_subscription_cb(client, callback_query):
    user_id = callback_query.from_user.id
    # wait a bit to ensure Telegram updates new member join
    await asyncio.sleep(2)
    if await is_subscribed(user_id):
        await callback_query.answer("✅ Verified! You can now use the bot.", show_alert=True)
        await start_cmd(client, callback_query.message)
    else:
        await callback_query.answer(
            "❌ You haven't joined the channel yet! Make sure you joined and try again.",
            show_alert=True
        )

# -------- MULTI-CHUNK DOWNLOAD HANDLER ----------
async def download_file(url, filepath, status):
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=40)) as session:
        async with session.head(url) as resp:
            total_size = int(resp.headers.get("Content-Length", 0))

        chunk_size = 16 * 1024 * 1024  # 16MB per chunk
        tasks = []
        downloaded_data = [None] * ((total_size // chunk_size) + 1)
        start_time = time.time()
        last_update = start_time

        async def download_chunk(idx, start, end):
            nonlocal last_update
            headers = {"Range": f"bytes={start}-{end}"}
            async with session.get(url, headers=headers) as r:
                data = await r.read()
                downloaded_data[idx] = data
                downloaded_bytes = sum(len(x) for x in downloaded_data if x)
                if time.time() - last_update > 1.0:
                    text = await progress_bar(downloaded_bytes, total_size, start_time, "📥 Downloading")
                    try:
                        await status.edit_text(text)
                    except:
                        pass
                    last_update = time.time()

        for i in range(0, total_size, chunk_size):
            start = i
            end = min(i + chunk_size - 1, total_size - 1)
            idx = i // chunk_size
            tasks.append(download_chunk(idx, start, end))

        await asyncio.gather(*tasks)

        with open(filepath, "wb") as f:
            for chunk in downloaded_data:
                f.write(chunk)

# -------- URL HANDLER (SUPER FAST) ----------
@app.on_message(filters.text & ~filters.command(["start"]))
async def url_handler(client, message):
    user_id = message.from_user.id
    if not await is_subscribed(user_id):
        await send_force_subscribe_prompt(message)
        return

    url = message.text.strip()
    filename = url.split("/")[-1].split("?")[0]
    ext = os.path.splitext(filename)[-1].lower()
    if ext not in Config.ALLOWED_EXTENSIONS:
        filename += ".mkv"

    filepath = os.path.join("downloads", filename)
    os.makedirs("downloads", exist_ok=True)
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
        await status.edit_text("✅ Upload completed! 🔥")

    except Exception as e:
        await status.edit_text(f"❌ Error: {e}")

    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

# -------- BROADCAST CMD ----------
@app.on_message(filters.command("broadcast") & filters.user(OWNER_IDS))
async def broadcast_handler(client, message):
    if message.reply_to_message:
        b_msg = message.reply_to_message
    elif len(message.command) > 1:
        b_msg = message.text.split(maxsplit=1)[1]
    else:
        await message.reply_text("⚠️ Usage:\nReply or /broadcast Your text")
        return

    sent, failed = 0, 0
    users = users_col.find({}).sort("user_id", 1)
    total = users_col.count_documents({})
    status = await message.reply_text(f"📢 Broadcasting started...\n👥 Total Users: {total}")

    for user in users:
        uid = user["user_id"]
        try:
            if hasattr(b_msg, "photo") and b_msg.photo:
                await app.send_photo(uid, b_msg.photo.file_id, caption=b_msg.caption or "")
            elif hasattr(b_msg, "video") and b_msg.video:
                await app.send_video(uid, b_msg.video.file_id, caption=b_msg.caption or "")
            elif hasattr(b_msg, "document") and b_msg.document:
                await app.send_document(uid, b_msg.document.file_id, caption=b_msg.caption or "")
            elif isinstance(b_msg, str):
                await app.send_message(uid, b_msg)
            else:
                continue

            sent += 1
            await asyncio.sleep(0.05)
            if sent % 20 == 0:
                await status.edit_text(
                    f"📢 Broadcasting...\n👥 Total Users: {total}\n📩 Sent: {sent}\n⚠️ Failed: {failed}"
                )
        except Exception:
            failed += 1
            continue

    await status.edit_text(
        f"✅ Broadcast completed!\n\n👥 Total Users: {total}\n📩 Sent: {sent}\n⚠️ Failed: {failed}"
    )

# ---------------- RUN ----------------
print("Madara URL Uploader Bot started... SUPER SPEED MODE ✅")
app.run()
