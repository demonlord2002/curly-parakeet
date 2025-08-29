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

# ---------------- COOLDOWN ----------------
user_cooldowns = {}
COOLDOWN_TIME = 120  # 2 minutes cooldown

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
        [
            InlineKeyboardButton("💜 Owner", url=f"https://t.me/{Config.OWNER_USERNAME}"),
            InlineKeyboardButton("🌸 Support", url=f"https://t.me/{Config.SUPPORT_CHANNEL.replace('@','')}")
        ]
    ])

    start_image_url = "YOUR_START_IMAGE_URL_HERE"  # <-- Replace this with your image URL

    await message.reply_photo(
        photo=start_image_url,
        caption=(
            f"💜🌸 **Rin's Ninja Uploader** 🌸💜\n\n"
            f"👋 Hey **{message.from_user.first_name}**! Rin’s on duty! 🥷✨\n"
            "🌿 I’ll guard your files like a true ninja!\n"
            "▶️ Send me any **Direct Video URL** (.mp4/.mkv) ⬇️\n"
            "⚡ I’ll **swiftly download & upload** it at lightning speed ⚡\n"
            "💫 **Full-size transfers safely delivered!** 💫\n"
            "🌸 Trust Rin, your files are in ninja hands! 🌸"
        ),
        reply_markup=btn
    )


# -------- VERIFY CALLBACK ----------
@app.on_callback_query(filters.regex("verify_sub"))
async def verify_subscription_cb(client, callback_query):
    if await is_subscribed(callback_query.from_user.id):
        await callback_query.message.edit_text("✅ Verified! Welcome to Rin Family ❤️")
        await start_cmd(client, callback_query.message)
    else:
        await callback_query.answer("❌ Not subscribed yet! Join first ⚡", show_alert=True)

# -------- SAFE STREAMING DOWNLOADER ---------
async def download_file(url, filepath, status):
    start_time = time.time()
    downloaded = 0
    chunk_size = 16 * 1024 * 1024  # 16 MB chunks
    last_update = 0

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            total_size = int(resp.headers.get("Content-Length", 0))
            with open(filepath, "wb") as f:
                async for chunk in resp.content.iter_chunked(chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if time.time() - last_update > 2 or downloaded == total_size:
                            last_update = time.time()
                            text = await progress_bar(downloaded, total_size, start_time, "📥 Downloading")
                            try: 
                                await status.edit_text(text)
                            except: 
                                pass

# -------- URL HANDLER WITH COOLDOWN ----------
@app.on_message(filters.text & ~filters.command(["start"]))
async def url_handler(client, message):
    user_id = message.from_user.id

    # Owner bypass cooldown
    if user_id not in OWNER_IDS:
        last_time = user_cooldowns.get(user_id, 0)
        if time.time() - last_time < COOLDOWN_TIME:
            await message.reply_text(f"⏳ Please wait {int(COOLDOWN_TIME - (time.time() - last_time))}s before next upload!")
            return
        user_cooldowns[user_id] = time.time()

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
        # Download
        await download_file(url, filepath, status)
        await status.edit_text("✅ Download completed. Starting upload...")

        # Upload with progress
        up_start = time.time()
        last_update = 0
        async def upload_progress(current, total):
            nonlocal last_update
            now = time.time()
            if now - last_update >= 2 or current == total:
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

# ---------------- BROADCAST ----------------
@app.on_message(filters.command("broadcast") & filters.user(OWNER_IDS))
async def broadcast_handler(client, message):
    # Determine broadcast content
    if message.reply_to_message:
        b_msg = message.reply_to_message
    elif len(message.command) > 1:
        b_msg = message.text.split(maxsplit=1)[1]
    else:
        await message.reply_text("⚠️ Usage:\nReply to a message with /broadcast\nOr use: /broadcast Your text")
        return

    sent, failed = 0, 0
    users = list(users_col.find({}))
    total = len(users)
    status = await message.reply_text(f"📢 Broadcasting started...\n👥 Total Users: {total}")

    for user in users:
        try:
            uid = user["user_id"]

            # Media broadcast
            if hasattr(b_msg, "photo") and b_msg.photo:
                await app.send_photo(uid, b_msg.photo.file_id, caption=b_msg.caption or "")
            elif hasattr(b_msg, "video") and b_msg.video:
                await app.send_video(uid, b_msg.video.file_id, caption=b_msg.caption or "")
            elif hasattr(b_msg, "document") and b_msg.document:
                await app.send_document(uid, b_msg.document.file_id, caption=b_msg.caption or "")
            # Text broadcast
            elif isinstance(b_msg, str):
                await app.send_message(uid, b_msg)
            else:
                continue

            sent += 1
            await asyncio.sleep(0.2)  # small delay to avoid FloodWait

        except Exception:
            failed += 1
            continue

    await status.edit_text(
        f"✅ Broadcast completed!\n\n"
        f"👥 Total Users: {total}\n"
        f"📩 Sent: {sent}\n"
        f"⚠️ Failed: {failed}"
    )

# ---------------- RUN ----------------
print("Madara URL Uploader Bot started... 🚀 FULL-SIZE STREAMING + BROADCAST Mode ✅")
app.run()
