import os

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

OWNER_IDS = list(map(int, os.getenv("OWNER_IDS").split(",")))

emails = os.getenv("MEGA_EMAILS").split(",")
passwords = os.getenv("MEGA_PASSWORDS").split(",")
MEGA_ACCOUNTS = [{"email": e, "password": p} for e, p in zip(emails, passwords)]

TMP_DOWNLOAD_PATH = "/tmp"
