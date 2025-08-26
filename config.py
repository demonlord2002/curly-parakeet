import os

# ========== Telegram API ==========
API_ID = int(os.environ.get("API_ID", "123456"))  # Replace with your API_ID
API_HASH = os.environ.get("API_HASH", "your_api_hash_here")  # Replace with your API_HASH
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token_here")  # Replace with your Bot Token

# ========== Bot Owner IDs ==========
OWNER_IDS = list(map(int, os.environ.get("OWNER_IDS", "123456789").split(",")))  # Comma separated IDs

# ========== MongoDB ==========
MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://username:password@cluster0.mongodb.net/dbname?retryWrites=true&w=majority")

# ========== Log Channel ==========
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "-1001234567890"))  # Telegram channel ID for logging

# ========== Web Server Settings ==========
WEB_PORT = int(os.environ.get("WEB_PORT", 8080))  # Heroku port
WEB_URL = os.environ.get("WEB_URL", "https://yourappname.herokuapp.com")  # Your Heroku app URL
