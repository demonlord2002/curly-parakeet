import os
import re
import aiohttp
import asyncio
import time
from urllib.parse import urljoin
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
    diff = now - start if now > start else 1
    percent = (current * 100 / total) if total else 0
    speed = (current / diff) if diff else 0
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
    except UserNotParticipant:
        return False
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await is_subscribed(user_id)
    except Exception as e:
        print(f"[is_subscribed] Error: {e}")
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
        {"$set": {"first_name": message.from_user.first_name, "username": message.from_user.username, "joined_at": time.time()}},
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
        await callback_query.message.edit_text("✅ Verified! Welcome to Rin Family ❤️")
        await start_cmd(client, callback_query.message)
    else:
        await callback_query.answer("❌ Not subscribed yet! Join first ⚡", show_alert=True)

# ---------------- XHAMSTER / GENERIC EXTRACTOR ----------------
# Tries multiple patterns to get a direct mp4 URL.
# If only .m3u8 is available, we will download .ts segments and produce an .mp4 file.

async def fetch_text(session, url):
    async with session.get(url, allow_redirects=True, ssl=False) as r:
        return await r.text()

async def extract_mp4_from_html(html):
    """
    Try multiple regex patterns to find mp4/m3u8 links embedded in HTML/JSON.
    Returns first match or None.
    """
    patterns = [
        r'"(?P<u>https?://[^"]+?\.mp4[^"]*)"',             # "https://...mp4"
        r"'(?P<u>https?://[^']+?\.mp4[^']*)'",             # 'https://...mp4'
        r'"(?P<u>https?://[^"]+?\.m3u8[^"]*)"',            # m3u8 often present
        r'source src="(?P<u>https?://[^"]+?\.m3u8[^"]*)"', # <source src="...m3u8">
        r'"(?P<u>https?://[^"]+?\.ts[^"]*)"',              # sometimes .ts absolute
        r'"(?P<u>https?://(?:www\.)?xhcdn[^"]+?\.mp4[^"]*)"', # xhcdn
        r'file:\s*"(?P<u>https?://[^"]+?\.mp4[^"]*)"',     # file: "https://...mp4"
        r'"(?P<u>https?://[^"]+?/videos/[^"]+?\.mp4[^"]*)"',
    ]
    for p in patterns:
        m = re.search(p, html)
        if m:
            return m.group("u").replace("\\/", "/")
    return None

async def extract_xhamster_or_generic(url):
    """
    Fetch page and try to extract direct mp4 or m3u8 URL.
    Returns tuple (kind, url) where kind in {"mp4","m3u8"} or (None, None)
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; Mobile) Chrome/120 Safari/537.36",
        "Referer": url,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            html = await fetch_text(session, url)
        except Exception as e:
            print("[extract] fetch page error:", e)
            return None, None

    # Try direct mp4/m3u8 in HTML
    media = await extract_mp4_from_html(html)
    if media:
        if ".mp4" in media:
            return "mp4", media
        if ".m3u8" in media:
            return "m3u8", media

    # Try JSON-like configs often used by players
    # Search for mp4 inside embedded JSON or JS objects
    m1 = re.search(r'["\'](https?://[^"\']+?\.m3u8[^"\']*)["\']', html)
    m2 = re.search(r'["\'](https?://[^"\']+?\.mp4[^"\']*)["\']', html)
    if m2:
        return "mp4", m2.group(1).replace("\\/", "/")
    if m1:
        return "m3u8", m1.group(1).replace("\\/", "/")

    # Try vendor-specific initial state
    js_init = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', html, flags=re.S)
    if js_init:
        blob = js_init.group(1)
        m = re.search(r'https?:\/\/[^"\'\\]+?\.mp4', blob)
        if m:
            return "mp4", m.group(0)
        m2 = re.search(r'https?:\/\/[^"\'\\]+?\.m3u8', blob)
        if m2:
            return "m3u8", m2.group(0)

    # fallback: any m3u8 in HTML
    m3 = re.search(r'https?://[^"\']+?\.m3u8[^"\']*', html)
    if m3:
        return "m3u8", m3.group(0)

    return None, None

# ---------------- DOWNLOAD HELPERS ----------------

async def download_stream_to_file(session, stream_url, filepath, status, user_id, start_time=None):
    """
    Download a single URL (mp4 or ts chunk) streaming to file, with progress updates.
    Appends to file so we can build from segments.
    """
    chunk_size = 8 * 1024 * 1024
    last_update = 0
    if start_time is None:
        start_time = time.time()

    async with session.get(stream_url, allow_redirects=True, ssl=False) as resp:
        if resp.status >= 400:
            raise Exception(f"HTTP {resp.status} for {stream_url}")

        total_size = int(resp.headers.get("Content-Length", 0)) or None
        mode = "ab"
        with open(filepath, mode) as f:
            async for chunk in resp.content.iter_chunked(chunk_size):
                if user_id in active_tasks and active_tasks[user_id].cancelled():
                    raise asyncio.CancelledError
                if chunk:
                    f.write(chunk)
                    now = time.time()
                    if now - last_update > 2:
                        last_update = now
                        # use current file size as current
                        current = os.path.getsize(filepath)
                        try:
                            text = await progress_bar(current, total_size or current, start_time, "📥 Downloading")
                            await status.edit_text(text)
                        except:
                            pass

# m3u8 parser + downloader (simple)
async def download_m3u8_and_merge(session, m3u8_url, filepath, status, user_id):
    # fetch playlist
    async with session.get(m3u8_url, allow_redirects=True, ssl=False) as r:
        if r.status >= 400:
            raise Exception(f"Failed playlist fetch: {r.status}")
        playlist = await r.text()

    base = m3u8_url.rsplit("/", 1)[0] + "/"
    lines = [ln.strip() for ln in playlist.splitlines() if ln and not ln.startswith("#")]

    # if master playlist (contains other m3u8), choose highest bandwidth or first
    if any(ln.endswith(".m3u8") for ln in lines):
        child = None
        variant_match = re.search(r'BANDWIDTH=(\d+).*?\n(https?://[^\n]+\.m3u8)', playlist)
        if variant_match:
            child = variant_match.group(2)
        else:
            for ln in lines:
                if ln.endswith(".m3u8"):
                    child = urljoin(base, ln)
                    break
        if child:
            return await download_m3u8_and_merge(session, child, filepath, status, user_id)

    seg_urls = []
    for ln in lines:
        if ln.startswith("http"):
            seg_urls.append(ln)
        else:
            seg_urls.append(urljoin(base, ln))

    if os.path.exists(filepath):
        os.remove(filepath)

    start_time = time.time()
    for seg in seg_urls:
        await download_stream_to_file(session, seg, filepath, status, user_id, start_time)

    # note: resulting file may be .ts stream; we keep .mp4 extension for compatibility

# -------- TRUE DIRECT DOWNLOADER (updated) ---------
async def download_file(url, filepath, status, user_id):
    """
    New logic:
      - If url is direct mp4 -> stream to file
      - If url is m3u8 -> fetch segments and merge
      - If url is a page (xhamster) -> extract actual mp4/m3u8 then download
    """
    start_time = time.time()
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; Mobile) Chrome/120 Safari/537.36",
        "Referer": url,
    }

    kind = None
    media_url = url

    # If URL doesn't look like direct media, attempt extractor
    if not re.search(r'\.(mp4|mkv|avi|mov|ts|m3u8)(?:$|\?)', url, flags=re.I):
        extracted_kind, extracted_url = await extract_xhamster_or_generic(url)
        if extracted_kind and extracted_url:
            kind = extracted_kind
            media_url = extracted_url
        else:
            # extractor failed; still attempt to download the URL
            media_url = url
    else:
        if re.search(r'\.m3u8', url, flags=re.I):
            kind = "m3u8"
        elif re.search(r'\.mp4|\.ts', url, flags=re.I):
            kind = "mp4"

    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            if kind == "m3u8" or (media_url and media_url.endswith(".m3u8")):
                if not filepath.lower().endswith(".mp4"):
                    filepath = os.path.splitext(filepath)[0] + ".mp4"
                await status.edit_text("🔍 Detected m3u8 playlist — downloading segments...")
                await download_m3u8_and_merge(session, media_url, filepath, status, user_id)
            else:
                await status.edit_text("🔍 Detected direct file — streaming download...")
                await download_stream_to_file(session, media_url, filepath, status, user_id, start_time=start_time)

            total = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            text = await progress_bar(total, total, start_time, "📥 Downloading")
            try:
                await status.edit_text(text)
            except:
                pass

        except asyncio.CancelledError:
            await status.edit_text("❌ Download cancelled by user!")
            if os.path.exists(filepath):
                os.remove(filepath)
            raise
        except Exception as e:
            # re-raise so outer task can handle and show message
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

    # filename extraction & sanitize
    raw_name = url.split("/")[-1].split("?")[0] or "video"
    raw_name = re.sub(r'[^A-Za-z0-9_\-\.]+', '_', raw_name)
    if not re.search(r'\.(mp4|mkv|avi|mov)$', raw_name, flags=re.I):
        filename = raw_name + ".mp4"
    else:
        filename = raw_name

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

            if user_id not in OWNER_IDS:
                user_cooldowns[user_id] = time.time()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            try:
                await status.edit_text(f"❌ Error while downloading: {e}")
            except:
                pass
            print("[task] error:", e)
        finally:
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass
            active_tasks.pop(user_id, None)

    t = asyncio.create_task(task())
    active_tasks[user_id] = t

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
    if message.reply_to_message:
        b_msg = message.reply_to_message
    elif len(message.command) > 1:
        b_msg = message.text.split(maxsplit=1)[1]
    else:
        await message.reply_text(
            "⚠️ Usage:\nReply to a message with /broadcast\nOr use: /broadcast Your text"
        )
        return

    sent, failed = 0, 0
    users = list(users_col.find({}))
    total = len(users)
    status = await message.reply_text(f"📢 Broadcasting started...\n👥 Total Users: {total}")

    for user in users:
        try:
            uid = user["user_id"]
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
            await asyncio.sleep(0.2)

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
print("Rin URL Uploader Bot started... 🚀 FULL-SIZE STREAMING + XHAMSTER/M3U8 FIX ✅")
app.run()
