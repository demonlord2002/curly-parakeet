import os

class Config:
    API_ID = int(os.getenv("API_ID", "12345"))  # get from my.telegram.org
    API_HASH = os.getenv("API_HASH", "your_api_hash")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")

    # Allowed extensions
    ALLOWED_EXTENSIONS = [".mkv", ".mp4"]

    # Channels & Owner
    SUPPORT_CHANNEL = "https://t.me/Fallen_Angels_Team"
    OWNER_USERNAME = "SunsetOfMe"
  
