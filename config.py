import os

API_ID = int(os.getenv("API_ID", "0"))           # default 0 if missing
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# OWNER_IDS: comma-separated IDs
OWNER_IDS = list(map(int, os.getenv("OWNER_IDS", "").split(","))) if os.getenv("OWNER_IDS") else []

# MEGA accounts: emails and passwords comma-separated
emails = os.getenv("MEGA_EMAILS", "").split(",") if os.getenv("MEGA_EMAILS") else []
passwords = os.getenv("MEGA_PASSWORDS", "").split(",") if os.getenv("MEGA_PASSWORDS") else []
MEGA_ACCOUNTS = [{"email": e, "password": p} for e, p in zip(emails, passwords)]

TMP_DOWNLOAD_PATH = "/tmp"
