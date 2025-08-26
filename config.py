import os

# ========== Telegram API ==========
API_ID = int(os.environ.get("API_ID", "27758016"))  # Replace with your API_ID
API_HASH = os.environ.get("API_HASH", "8d34cfffe27ab461eabbf0091b1a27df")  # Replace with your API_HASH
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8458120677:AAE-_r9xzg3Tg1PchwlwUmMPcBUUqmOP1MM")  # Replace with your Bot Token

# ========== Bot Owner IDs ==========
OWNER_IDS = list(map(int, os.environ.get("OWNER_IDS", "7590607726").split(",")))  # Comma separated IDs

# ========== MongoDB ==========
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://username:password@cluster0.mongodb.net/dbname?retryWrites=true&w=majority")

# ========== Log Channel ==========
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "-1002718440283"))  # Telegram channel ID for logging

# ========== Web Server Settings ==========
WEB_PORT = int(os.environ.get("WEB_PORT", 8080))  # Heroku port
WEB_URL = os.environ.get("WEB_URL", "https://dead7.herokuapp.com")  # Your Heroku app URL
