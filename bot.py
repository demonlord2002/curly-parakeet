import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient
from config import API_ID, API_HASH, BOT_TOKEN, OWNER_IDS, MONGO_URI, LOG_CHANNEL, WEB_PORT, WEB_URL
from aiohttp import web

# ----------------- MongoDB Setup -----------------
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client["file_to_link_bot"]
files_collection = db["files"]

# ----------------- Pyrogram Client -----------------
app = Client("file_link_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ----------------- Helper Functions -----------------
async def save_file_info(file_id, file_name, file_size, uploader_id):
    await files_collection.insert_one({
        "file_id": file_id,
        "file_name": file_name,
        "file_size": file_size,
        "uploader_id": uploader_id
    })

def generate_download_link(file_id):
    return f"{WEB_URL}/download/{file_id}"

# ----------------- Bot Handlers -----------------
@app.on_message(filters.private & filters.document)
async def handle_file(client, message):
    if message.from_user.id not in OWNER_IDS:
        await message.reply_text("❌ You are not authorized to upload files.")
        return

    file = message.document
    file_id = file.file_id
    file_name = file.file_name
    file_size = file.file_size

    # Save file info in MongoDB
    await save_file_info(file_id, file_name, file_size, message.from_user.id)

    # Send download link
    download_link = generate_download_link(file_id)
    await message.reply_text(
        f"✅ File uploaded successfully!\n\n📥 Download Link:\n{download_link}",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Download Now", url=download_link)]]
        )
    )

    # Log in channel
    await app.send_message(
        LOG_CHANNEL,
        f"📂 New File Uploaded:\n\n👤 User: {message.from_user.first_name} [{message.from_user.id}]\n📝 Name: {file_name}\n📦 Size: {file_size} bytes\n🔗 Link: {download_link}"
    )

# ----------------- Web Server -----------------
routes = web.RouteTableDef()

@routes.get("/download/{file_id}")
async def download_file(request):
    file_id = request.match_info["file_id"]
    file_doc = await files_collection.find_one({"file_id": file_id})
    if not file_doc:
        return web.Response(text="File not found!", status=404)

    return web.Response(text=f"{WEB_URL}/file/{file_id}")

# ----------------- Start Web Server -----------------
async def start_web():
    app_web = web.Application()
    app_web.add_routes(routes)
    runner = web.AppRunner(app_web)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", WEB_PORT)
    await site.start()
    print(f"🌐 Web server running on port {WEB_PORT}")

# ----------------- Main -----------------
async def main():
    await start_web()
    await app.start()
    print("🤖 Bot is running...")
    await idle()

if __name__ == "__main__":
    from pyrogram import idle
    asyncio.run(main())
