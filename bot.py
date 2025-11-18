import os
import aiohttp
import asyncio
import time
import json
import re
import m3u8
import ffmpeg
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pymongo import MongoClient
from config import Config

app = Client(
    "rin_url_uploader",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

mongo = MongoClient(Config.MONGO_URI)
db = mongo["rin_bot"]
users_col = db["users"]

active_tasks = {}

# -------------------- BASIC PROGRESS BAR --------------------
async def progress_bar(current, total, start, stage):
    now = time.time()
    diff = now - start
    percent = current * 100 / total if total else 0
    speed = current / diff if diff else 0
    bar = "▓" * int(percent/10) + "░" * (10 - int(percent/10))
    eta = (total - current) / speed if speed else 0
    return f"{stage}: {bar} {percent:.2f}% | {speed/1024/1024:.2f} MB/s | ETA {int(eta)}s"

# --------------------------------------------------------------
#      XHAMSTER VIDEO URL → DIRECT MP4 EXTRACTOR
# --------------------------------------------------------------
async def extract_xhamster(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Android 10)",
            "Accept": "*/*"
        }
        async with aiohttp.ClientSession(headers=headers) as s:
            async with s.get(url) as r:
                html = await r.text()

        # Try direct mp4 URL pattern
        match = re.search(r'"videoUrl":"(https.*?\.mp4.*?)"', html)
        if match:
            return match.group(1).replace("\\/", "/")

        # Try highest quality pattern
        match2 = re.findall(r'"format":"(\d+.*?)","videoUrl":"(https.*?\.mp4.*?)"', html)
        if match2:
            # Sort by format (e.g., 720p, 480p)
            best = sorted(match2, key=lambda x: int(x[0].replace("p","").replace("P","")), reverse=True)[0]
            return best[1].replace("\\/", "/")

        # New XHamster CDN key extraction
        match3 = re.search(r'"720p":"(https.*?\.mp4.*?)"', html)
        if match3:
            return match3.group(1).replace("\\/", "/")

        # Fallback generic mp4
        match4 = re.search(r'(https.*?\.mp4.*?)"', html)
        if match4:
            return match4.group(1).replace("\\/", "/")

        return None

    except Exception as e:
        print("EXTRACTOR ERROR:", e)
        return None


# --------------------------------------------------------------
#               M3U8 → MP4 DOWNLOADER
# --------------------------------------------------------------
async def download_m3u8(url, output_file, status):
    start = time.time()

    async with aiohttp.ClientSession() as session:
        playlist = m3u8.load(url)
        segments = playlist.segments

        temp_folder = "segments"
        os.makedirs(temp_folder, exist_ok=True)

        seg_files = []
        count = 0
        total = len(segments)

        for seg in segments:
            count += 1
            seg_url = seg.uri

            seg_path = f"{temp_folder}/{count}.ts"
            seg_files.append(seg_path)

            async with session.get(seg_url) as r:
                with open(seg_path, "wb") as f:
                    f.write(await r.read())

            if count % 5 == 0:
                try:
                    txt = await progress_bar(count, total, start, "📥 M3U8 Segments")
                    await status.edit_text(txt)
                except:
                    pass

    # MERGE TS → MP4
    (
        ffmpeg
        .input(f"{temp_folder}/%d.ts", pattern_type="sequence")
        .output(output_file, vcodec="copy", acodec="copy")
        .run(overwrite_output=True)
    )

    for f in seg_files:
        if os.path.exists(f):
            os.remove(f)
    os.rmdir(temp_folder)

# --------------------------------------------------------------
#              NORMAL DIRECT FILE DOWNLOADER
# --------------------------------------------------------------
async def normal_download(url, path, status):
    start = time.time()
    downloaded = 0

    async with aiohttp.ClientSession() as s:
        async with s.get(url) as r:
            total = int(r.headers.get("Content-Length", 0))

            with open(path, "wb") as f:
                async for chunk in r.content.iter_chunked(2 * 1024 * 1024):
                    f.write(chunk)
                    downloaded += len(chunk)

                    try:
                        txt = await progress_bar(downloaded, total, start, "📥 Downloading")
                        await status.edit_text(txt)
                    except:
                        pass

# --------------------------------------------------------------
#                          MAIN URL HANDLER
# --------------------------------------------------------------
@app.on_message(filters.text & ~filters.command(["start"]))
async def handle_url(client, message):
    url = message.text.strip()
    user_id = message.from_user.id

    status = await message.reply_text("🔍 Checking link...")

    # -------- XHAMSTER CHECK --------
    if "xhamster" in url or "xh" in url:
        await status.edit_text("🔍 Extracting XHamster Video...")
        direct = await extract_xhamster(url)
        if not direct:
            return await status.edit_text("❌ Failed to extract XHamster link!")

        url = direct

    # -------- M3U8 CHECK --------
    if url.endswith(".m3u8"):
        filename = f"xhamster_{int(time.time())}.mp4"
        filepath = f"downloads/{filename}"

        await status.edit_text("📥 M3U8 Detected — Downloading Segments...")
        await download_m3u8(url, filepath, status)

        await message.reply_document(filepath)
        os.remove(filepath)
        return

    # -------- NORMAL DOWNLOAD --------
    filename = url.split("/")[-1].split("?")[0]
    if "." not in filename:
        filename += ".mp4"

    filepath = f"downloads/{filename}"

    await status.edit_text("📥 Starting direct download...")
    await normal_download(url, filepath, status)

    await status.edit_text("📤 Uploading...")
    await message.reply_document(filepath)
    os.remove(filepath)

# --------------------------------------------------------------
app.run()
