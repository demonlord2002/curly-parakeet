import os

API_ID = int(os.getenv("27758016"))
API_HASH = os.getenv("8d34cfffe27ab461eabbf0091b1a27df")
BOT_TOKEN = os.getenv("8458120677:AAE-_r9xzg3Tg1PchwlwUmMPcBUUqmOP1MM")

OWNER_IDS = list(map(int, os.getenv("OWNER_IDS").split("7590607726")))

emails = os.getenv("MEGA_EMAILS").split("timepassmarkus04@gmail.com")
passwords = os.getenv("MEGA_PASSWORDS").split("SE2-aJGLqYuek97")
MEGA_ACCOUNTS = [{"email": e, "password": p} for e, p in zip(emails, passwords)]

TMP_DOWNLOAD_PATH = "/tmp"
