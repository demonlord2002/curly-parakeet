import os

class Config:
    # Telegram API
    API_ID = int(os.getenv("API_ID", "22201946"))         # your api_id from my.telegram.org
    API_HASH = os.getenv("API_HASH", "f4e7f0de47a09671133ecafa6920ebbe")   # your api_hash from my.telegram.org
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8275918271:AAG9tIjh-5mWRvrz2lKMhMQH8NHdBz4_IgE") # your bot token from BotFather

    # MongoDB
    MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://drdoom2003p:drdoom2003p@cluster0.fnhjrtn.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")  # MongoDB URI

    # Owner / Admin
    OWNER_ID = int(os.getenv("OWNER_ID", "7590607726"))   # Your Telegram ID
    OWNER_USERNAME = os.getenv("OWNER_USERNAME", "SunsetOfMe")  # Optional for buttons

    # Support Channel (for help / info only)
    SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "Fallen_Angels_Team")

    # Force Subscribe Channel (must join before using bot)
    FORCE_SUB_CHANNEL = os.getenv("FORCE_SUB_CHANNEL", "Fallen_Angels_Team")

    # Allowed file extensions
    ALLOWED_EXTENSIONS = [".mp4", ".mkv"]
    
