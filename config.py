# config.py

# ------------------- TELEGRAM -------------------
API_ID = 123456                # Your Telegram API ID (from https://my.telegram.org)
API_HASH = "your_api_hash"     # Your Telegram API HASH
BOT_TOKEN = "your_bot_token"   # Bot token from BotFather

# ------------------- OWNER -------------------
OWNER_IDS = [
    123456789,  # Add your Telegram user ID
    # Add more owner IDs if needed
]

# ------------------- MEGA ACCOUNTS -------------------
# Add up to 10 MEGA accounts. The bot rotates automatically when storage full.
# Format: {"email": "your_email", "password": "your_password"}
MEGA_ACCOUNTS = [
    {"email": "mega1@example.com", "password": "password1"},
    {"email": "mega2@example.com", "password": "password2"},
    {"email": "mega3@example.com", "password": "password3"},
    # Add more up to 10
]

# ------------------- TEMPORARY DOWNLOAD PATH -------------------
# Heroku and VPS compatible
TMP_DOWNLOAD_PATH = "/tmp"
