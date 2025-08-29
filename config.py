import os

API_ID = int(os.getenv("API_ID", "22201946"))
API_HASH = os.getenv("API_HASH", "f4e7f0de47a09671133ecafa6920ebbe")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8458120677:AAE-_r9xzg3Tg1PchwlwUmMPcBUUqmOP1MM")
BOT_USERNAME = os.getenv("BOT_USERNAME", "FastFileLinkerBot")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://drdoom2003p:drdoom2003p@cluster0.fnhjrtn.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "7590607726").split(",") if x.strip().isdigit()]

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "2048"))
