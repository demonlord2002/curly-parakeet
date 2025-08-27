import os

# Get the bot token from environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8458120677:AAE-_r9xzg3Tg1PchwlwUmMPcBUUqmOP1MM')

# Heroku app name (set this in your Heroku config vars)
HEROKU_APP_NAME = os.environ.get('HEROKU_APP_NAME', 'devm09')

# Port for Heroku
PORT = int(os.environ.get('PORT', 8443))

# Allowed file types
ALLOWED_EXTENSIONS = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm']

# Maximum file size in bytes (2GB)
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024

# Admin user ID (optional)
ADMIN_ID = os.environ.get('ADMIN_ID', '7590607726')
