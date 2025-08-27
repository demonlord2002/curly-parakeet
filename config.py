import os

# Get the bot token from environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')

# Heroku app name (set this in your Heroku config vars)
HEROKU_APP_NAME = os.environ.get('HEROKU_APP_NAME', '')

# Port for Heroku
PORT = int(os.environ.get('PORT', 8443))
