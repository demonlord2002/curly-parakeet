import os
import aiohttp
import asyncio
import time
import traceback
import urllib.parse
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import UserNotParticipant, FloodWait, PeerIdInvalid, FloodWait, ChatAdminRequired, BotBlocked, UserNotFound, InputUserDeactivated
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

# ---------------- OWNER ----------------
OWNER_IDS = [Config.OWNER_ID]

# ---------------- COOLDOWN ----------------
user_cooldowns = {}  # {user_id: last_task_completed_time}
COOLDOWN_TIME = 120  # 2 minutes cooldown

# ---------------- ACTIVE TASKS ----------------
active_tasks = {}  # {user_id: asyncio.Task}

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
        {"$set": {"first_name": message.from_user.first_name, "username": message.from_user.username, "joined_at": time.time()}},
        upsert=True
    )
    if not await is_subscribed(user_id):
        await send_force_subscribe_prompt(message)
        return

    btn = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💜 Owner", url=f"https://t.me/{Config.OWNER_USERNAME}"),
            InlineKeyboardButton("🌸 Support", url=f"https://t.me/{Config.SUPPORT_CHANNEL.replace('@','')}"),
        ]
    ])

    start_image_url = "https://graph.org/file/28a666c9d556b966df561-c11c02a8abe04be820.jpg"

    await message.reply_photo(
        photo=start_image_url,
        caption=(
            f"💜 **Rin's Ninja Uploader** 💜\n\n"
            f"👋 Hello **{message.from_user.first_name}**! Send a **Direct Video URL** and Rin will handle it swiftly! ⚡\n\n"
            f"💫 **Full-size uploads safely delivered!** 💫"
        ),
        reply_markup=btn
    )

# -------- VERIFY CALLBACK ----------
@app.on_callback_query(filters.regex("verify_sub"))
async def verify_subscription_cb(client, callback_query):
    if await is_subscribed(callback_query.from_user.id):
        try:
            await callback_query.message.edit_text("✅ Verified! Welcome to Rin Family ❤️")
        except Exception:
            pass
        # call start_cmd to show welcome (pass a fake message object by reusing callback message)
        await start_cmd(client, callback_query.message)
    else:
        await callback_query.answer("❌ Not subscribed yet! Join first ⚡", show_alert=True)

# -------- SAFE STREAMING DOWNLOADER ---------
async def download_file(url, filepath, status, user_id):
    start_time = time.time()
    downloaded = 0
    chunk_size = 16 * 1024 * 1024
    last_update = 0

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                total_size = int(resp.headers.get("Content-Length", 0))
                with open(filepath, "wb") as f:
                    async for chunk in resp.content.iter_chunked(chunk_size):
                        if user_id in active_tasks and active_tasks[user_id].cancelled():
                            raise asyncio.CancelledError
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
    except asyncio.CancelledError:
        try:
            await status.edit_text("❌ Download cancelled by user!")
        except: pass
        if os.path.exists(filepath):
            os.remove(filepath)
        raise
    except Exception as e:
        raise

# -------- URL HANDLER WITH COOLDOWN ----------
@app.on_message(filters.text & ~filters.command(["start", "cancel"]))
async def url_handler(client, message):
    user_id = message.from_user.id

    if not await is_subscribed(user_id):
        await send_force_subscribe_prompt(message)
        return

    # ---- COOLDOWN CHECK ----
    if user_id not in OWNER_IDS:
        last_done = user_cooldowns.get(user_id, 0)
        if time.time() - last_done < COOLDOWN_TIME:
            wait_time = int(COOLDOWN_TIME - (time.time() - last_done))
            await message.reply_text(f"⏳ Please wait {wait_time}s before starting your next upload!")
            return

    url = message.text.strip()
    filename = url.split("/")[-1].split("?")[0]
    if not any(filename.endswith(ext) for ext in Config.ALLOWED_EXTENSIONS):
        filename += ".mkv"

    os.makedirs("downloads", exist_ok=True)
    filepath = os.path.join("downloads", filename)
    status = await message.reply_text("📥 Starting download...")

    async def task():
        try:
            await download_file(url, filepath, status, user_id)
            await status.edit_text("✅ Download completed. Starting upload...")

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

            # ✅ UPDATE COOLDOWN AFTER TASK COMPLETION
            if user_id not in OWNER_IDS:
                user_cooldowns[user_id] = time.time()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            try:
                await status.edit_text(f"❌ Error: {e}")
            except: pass
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)
            active_tasks.pop(user_id, None)

    # Save task and run
    active_tasks[user_id] = asyncio.create_task(task())

# -------- CANCEL COMMAND ----------
@app.on_message(filters.command("cancel"))
async def cancel_handler(client, message):
    user_id = message.from_user.id
    task = active_tasks.get(user_id)
    if task:
        task.cancel()
        await message.reply_text("❌ Your current download/upload has been cancelled!")
    else:
        await message.reply_text("⚠️ No active download/upload to cancel!")

# ---------------- BROADCAST ----------------
@app.on_message(filters.command("broadcast") & filters.user(Config.OWNER_ID))
async def broadcast_handler(client, message):
    # Determine broadcast payload
    b_msg = None

    # Case 1: owner replied to a message -> forward that
    if message.reply_to_message:
        b_msg = message.reply_to_message
    else:
        # Case 2: /broadcast some text
        # Robustly extract text after the command and decode any url-encoding
        try:
            raw = message.text or ""
            # Remove command portion (/broadcast or /broadcast@BotName)
            parts = raw.split(maxsplit=1)
            if len(parts) > 1:
                text = parts[1]
                text = urllib.parse.unquote_plus(text)
                text = text.strip()
                if text:
                    b_msg = text
        except Exception:
            b_msg = None

    if not b_msg:
        await message.reply_text(
            "⚠️ Usage:\nReply to a message with /broadcast (to broadcast media)\nOr use: /broadcast Your text here"
        )
        return

    sent, failed = 0, 0
    users = list(users_col.find({}, {"user_id": 1}))
    total = len(users)
    status = await message.reply_text(f"📢 Broadcasting started...\n👥 Total Users: {total}")

    for u in users:
        uid = u.get("user_id")
        if not uid:
            continue
        try:
            if hasattr(b_msg, "photo") and b_msg.photo:
                await app.send_photo(uid, b_msg.photo.file_id, caption=b_msg.caption or "")
            elif hasattr(b_msg, "video") and b_msg.video:
                await app.send_video(uid, b_msg.video.file_id, caption=b_msg.caption or "")
            elif hasattr(b_msg, "document") and b_msg.document:
                await app.send_document(uid, b_msg.document.file_id, caption=b_msg.caption or "")
            elif isinstance(b_msg, str):
                # plain text broadcast
                await app.send_message(uid, b_msg)
            else:
                # fallback: forward the message
                try:
                    await app.forward_messages(uid, message.chat.id, message.message_id)
                except Exception:
                    # if forwarding fails, just skip
                    raise

            sent += 1
            # small sleep to avoid hitting limits
            await asyncio.sleep(0.12)

        except (BotBlocked, UserNotFound, InputUserDeactivated, PeerIdInvalid):
            failed += 1
            continue
        except FloodWait as fw:
            # sleep and retry this user
            await asyncio.sleep(fw.x)
            try:
                # retry once
                if isinstance(b_msg, str):
                    await app.send_message(uid, b_msg)
                else:
                    await app.forward_messages(uid, message.chat.id, message.message_id)
                sent += 1
            except Exception:
                failed += 1
            continue
        except Exception as e:
            # unexpected error, count as failed and continue
            failed += 1
            continue

    try:
        await status.edit_text(
            f"✅ Broadcast completed!\n\n👥 Total Users: {total}\n📩 Sent: {sent}\n⚠️ Failed: {failed}"
        )
    except:
        pass


# ---------------- RUN ----------------
print("Rin URL Uploader Bot started... 🚀 FULL-SIZE STREAMING + BROADCAST + CANCEL Mode ✅")
app.run()
