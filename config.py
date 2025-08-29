import os

class Config:
    API_ID = int(os.getenv("API_ID", "22201946"))  # get from my.telegram.org
    API_HASH = os.getenv("API_HASH", "f4e7f0de47a09671133ecafa6920ebbe")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8458120677:AAE-_r9xzg3Tg1PchwlwUmMPcBUUqmOP1MM")

    # Allowed extensions
    ALLOWED_EXTENSIONS = [".mkv", ".mp4"]

    # Channels & Owner
    SUPPORT_CHANNEL = "https://t.me/Fallen_Angels_Team"
    OWNER_USERNAME = "SunsetOfMe"
  
