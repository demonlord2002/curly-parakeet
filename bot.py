import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, HEROKU_APP_NAME, PORT

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! I'm a File to Link Bot. Send me any MP4 or MKV file and I'll give you a direct download link!"
    )

# Help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Just send me a video file (MP4/MKV) and I'll generate a direct download link for you!"
    )

# Handle video files
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        
        if message.video:
            file_id = message.video.file_id
            file_name = message.video.file_name or "video.mp4"
            file_size = message.video.file_size
        elif message.document:
            # Check if it's an MP4 or MKV file
            mime_type = message.document.mime_type
            file_name = message.document.file_name or "file"
            
            if mime_type not in ['video/mp4', 'video/x-matroska'] and not file_name.endswith(('.mp4', '.mkv')):
                await message.reply_text("Please send only MP4 or MKV files.")
                return
                
            file_id = message.document.file_id
            file_size = message.document.file_size
        else:
            await message.reply_text("Please send a video file.")
            return
        
        # Check file size (max 2GB for Telegram bots)
        if file_size > 2000 * 1024 * 1024:
            await message.reply_text("File is too large. Maximum size is 2GB.")
            return
        
        # Get file info
        file = await context.bot.get_file(file_id)
        
        # Generate direct download link
        if HEROKU_APP_NAME:
            # For Heroku deployment
            direct_link = f"https://{HEROKU_APP_NAME}.herokuapp.com/{file_id}/{file_name}"
        else:
            # For local development
            direct_link = file.file_path
        
        # Send the link to user
        await message.reply_text(
            f"Here's your direct download link:\n\n{direct_link}\n\n"
            f"File: {file_name}\n"
            f"Size: {file_size // (1024 * 1024)} MB\n\n"
            "Click the link to download the file directly."
        )
        
    except Exception as e:
        logger.error(f"Error handling video: {e}")
        await update.message.reply_text("Sorry, something went wrong. Please try again.")

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

def main():
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_video))
    application.add_error_handler(error_handler)
    
    # Start the bot
    if HEROKU_APP_NAME:
        # Running on Heroku
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"https://{HEROKU_APP_NAME}.herokuapp.com/{BOT_TOKEN}"
        )
    else:
        # Running locally
        application.run_polling()

if __name__ == "__main__":
    main()
