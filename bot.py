import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, HEROKU_APP_NAME, PORT, ALLOWED_EXTENSIONS, MAX_FILE_SIZE, ADMIN_ID

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store processed files temporarily (in production you might want to use a database)
file_store = {}

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Hi {user.first_name}! 👋\n\n"
        "I'm a File to Link Bot. Send me any video file (MP4, MKV, etc.) "
        "and I'll give you a direct download link!\n\n"
        "Use /help to see supported formats."
    )

# Help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🤖 <b>File to Link Bot Help</b>\n\n"
        "Just send me a video file and I'll generate a direct download link for you!\n\n"
        "📁 <b>Supported formats:</b>\n"
        "• MP4, MKV, AVI, MOV, WMV, FLV, WEBM\n\n"
        "⚙️ <b>Commands:</b>\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n"
        "/about - About this bot\n\n"
        "⚠️ <b>Note:</b> Maximum file size is 2GB"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')

# About command
async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = (
        "🔗 <b>File to Link Bot</b>\n\n"
        "This bot converts your files to direct download links.\n\n"
        "📦 <b>How it works:</b>\n"
        "1. Send me a video file\n"
        "2. I process it and generate a direct link\n"
        "3. You can share the link or download directly\n\n"
        "⚡ <b>Features:</b>\n"
        "• Fast direct download links\n"
        "• Support for multiple video formats\n"
        "• Simple and easy to use"
    )
    await update.message.reply_text(about_text, parse_mode='HTML')

# Handle video files
async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        user_id = message.from_user.id
        
        if message.video:
            file_id = message.video.file_id
            file_name = message.video.file_name or "video.mp4"
            file_size = message.video.file_size
            mime_type = message.video.mime_type or "video/mp4"
        elif message.document:
            # Check if it's a supported file type
            mime_type = message.document.mime_type or ""
            file_name = message.document.file_name or "file"
            file_ext = os.path.splitext(file_name)[1].lower()
            
            if (mime_type not in ['video/mp4', 'video/x-matroska', 'video/avi', 'video/quicktime', 
                                'video/x-ms-wmv', 'video/x-flv', 'video/webm'] and 
                file_ext not in ALLOWED_EXTENSIONS):
                await message.reply_text(
                    "❌ Unsupported file type. Please send only video files (MP4, MKV, AVI, MOV, WMV, FLV, WEBM)."
                )
                return
                
            file_id = message.document.file_id
            file_size = message.document.file_size
        else:
            await message.reply_text("Please send a video file.")
            return
        
        # Check file size
        if file_size > MAX_FILE_SIZE:
            await message.reply_text("❌ File is too large. Maximum size is 2GB.")
            return
        
        # Get file info
        file = await context.bot.get_file(file_id)
        
        # Store file information
        file_store[file_id] = {
            'file_name': file_name,
            'file_size': file_size,
            'mime_type': mime_type,
            'user_id': user_id
        }
        
        # Generate direct download link
        if HEROKU_APP_NAME:
            # For Heroku deployment
            direct_link = f"https://{HEROKU_APP_NAME}.herokuapp.com/file/{file_id}/{file_name}"
        else:
            # For local development
            direct_link = file.file_path
        
        # Format file size
        size_mb = file_size / (1024 * 1024)
        
        # Send the link to user
        await message.reply_text(
            f"✅ <b>File processed successfully!</b>\n\n"
            f"📁 <b>File:</b> <code>{file_name}</code>\n"
            f"📊 <b>Size:</b> {size_mb:.2f} MB\n\n"
            f"🔗 <b>Direct Download Link:</b>\n"
            f"<code>{direct_link}</code>\n\n"
            f"Click the link to download the file directly.",
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Error handling video: {e}")
        await update.message.reply_text("❌ Sorry, something went wrong. Please try again.")

# Error handler
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("❌ An error occurred. Please try again.")

def main():
    # Check if BOT_TOKEN is set
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN environment variable is not set!")
        return
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, handle_video))
    application.add_error_handler(error_handler)
    
    # Start the bot
    if HEROKU_APP_NAME:
        # Running on Heroku
        logger.info(f"Starting webhook on Heroku: {HEROKU_APP_NAME}")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=BOT_TOKEN,
            webhook_url=f"https://{HEROKU_APP_NAME}.herokuapp.com/{BOT_TOKEN}"
        )
    else:
        # Running locally
        logger.info("Starting polling locally...")
        application.run_polling()

if __name__ == "__main__":
    main()
