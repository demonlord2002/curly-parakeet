import os

class Config:
    # Telegram API
    API_ID = int(os.getenv("API_ID", ""))  # your api_id from my.telegram.org
    API_HASH = os.getenv("API_HASH", "")  # your api_hash from my.telegram.org
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")  # your bot token from BotFather

    # MongoDB
    MONGO_URI = os.getenv("MONGO_URI", "")  # MongoDB URI

    # Owner / Admin
    OWNER_ID = int(os.getenv("OWNER_ID", ""))  # Your Telegram ID
    OWNER_USERNAME = os.getenv("OWNER_USERNAME", "")  # Optional for buttons

    # Support Channel (for help / info only)
    SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "")

    # Force Subscribe Channel (must join before using bot)
    FORCE_SUB_CHANNEL = os.getenv("FORCE_SUB_CHANNEL", "")

    # Allowed file extensions
    ALLOWED_EXTENSIONS = [".mp4", ".mkv"]

