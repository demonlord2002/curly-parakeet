import os

class Config:
    # Telegram API
    API_ID = int(os.getenv("API_ID", "1234567"))         # your api_id from my.telegram.org
    API_HASH = os.getenv("API_HASH", "your_api_hash")   # your api_hash from my.telegram.org
    BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token") # your bot token from BotFather

    # MongoDB
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")  # MongoDB URI

    # Owner / Admin
    OWNER_ID = int(os.getenv("OWNER_ID", "123456789"))   # Your Telegram ID
    OWNER_USERNAME = os.getenv("OWNER_USERNAME", "YourUsername")  # Optional for buttons

    # Support / Force Subscribe Channel
    SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "YourChannelUsername") # e.g., madara_support

    # Allowed file extensions
    ALLOWED_EXTENSIONS = [".mp4", ".mkv"]
