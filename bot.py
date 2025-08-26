import os
import asyncio
import datetime
import time
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_IDS, MONGO_URI, LOG_CHANNEL, WEB_PORT, WEB_URL
from aiohttp import web
from pyrogram.errors import FloodWait

# ----------------- Ensure UTC Time -----------------
os.environ["TZ"] = "UTC"
try:
    time.tzset()
except Exception:
    pass
print("⏱ Current UTC time:", datetime.datetime.utcnow())

# ----------------- MongoDB Setup -----------------
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["file_to_link_bot"]
files_collection = db["files"]

# ----------------- Pyrogram Client -----------------
bot = Client(
    "file_link_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir="./sessions"
)

# ----------------- Helper Functions -----------------
async def save_file_info(file_id, file_name, file_size, uploader_id, message_id):
    await files_collection.insert_one({
        "file_id": file_id,
        "file_name": file_name,
        "file_size": file_size,
        "uploader_id": uploader_id,
        "message_id": message_id
    })

def generate_download_link(file_id):
    return f"{WEB_URL}/download/{file_id}"

# ----------------- Bot Handlers -----------------
@bot.on_message(filters.private & (filters.document | filters.video))
async def handle_file(client, message):
    if message.from_user.id not in OWNER_IDS:
        await message.reply_text("❌ You are not authorized to upload files.")
        return

    file = message.document or message.video
    file_id = file.file_id
    file_name = getattr(file, "file_name", f"{file.file_unique_id}.mp4")
    file_size = file.file_size

    # Save file info in MongoDB
    await save_file_info(file_id, file_name, file_size, message.from_user.id, message.id)

    # Generate download link
    download_link = generate_download_link(file_id)
    await message.reply_text(
        f"✅ File uploaded successfully!\n\n📥 Download Link:\n{download_link}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Download Now", url=download_link)]])
    )

    # Log in channel
    try:
        await bot.send_message(
            LOG_CHANNEL,
            f"📂 New File Uploaded:\n👤 User: {message.from_user.first_name} [{message.from_user.id}]\n"
            f"📝 Name: {file_name}\n📦 Size: {file_size} bytes\n🔗 Link: {download_link}"
        )
    except FloodWait as e:
        await asyncio.sleep(e.x)

# ----------------- Web Server -----------------
routes = web.RouteTableDef()

@routes.get("/download/{file_id}")
async def download_file(request):
    file_id = request.match_info["file_id"]
    file_doc = await files_collection.find_one({"file_id": file_id})
    if not file_doc:
        return web.Response(text="File not found!", status=404)

    try:
        msg = await bot.get_messages(chat_id=file_doc["uploader_id"], message_ids=file_doc["message_id"])
        file_path = await bot.download_media(msg, file_name=file_doc["file_name"])
    except Exception as e:
        print("❌ Error fetching file:", e)
        return web.Response(text="Error fetching file!", status=500)

    return web.FileResponse(
        file_path,
        headers={"Content-Disposition": f"attachment; filename={file_doc['file_name']}"}
    )

async def start_web():
    app_web = web.Application()
    app_web.add_routes(routes)
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", WEB_PORT)
    await site.start()
    print(f"🌐 Web server running on port {WEB_PORT}")

# ----------------- Main -----------------
async def run_bot():
    asyncio.create_task(start_web())

    retries = 0
    while retries < 10:
        try:
            await bot.start()
            print("🤖 Bot connected successfully!")
            await idle()
            break
        except Exception as e:
            retries += 1
            print(f"⚠️ Start failed (attempt {retries}): {e}")
            await asyncio.sleep(10)

    await bot.stop()
    print("❌ Bot stopped.")

if __name__ == "__main__":
    os.makedirs("./sessions", exist_ok=True)
    asyncio.run(run_bot())
