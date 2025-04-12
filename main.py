import os
import logging
import threading
import time
import sys
from app import app
from bot import setup_bot
from scheduler import start_scheduler

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('main.log')
    ]
)
logger = logging.getLogger(__name__)

def run_flask_app():
    """Run the Flask app in a separate thread."""
    # Use gunicorn in production instead of this
    try:
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Flask app error: {e}")
        # If port is in use, just log it but don't crash
        if "Address already in use" in str(e):
            logger.info("Port 5000 is already in use, continuing with bot functionality")
        else:
            logger.error(f"Unexpected Flask error: {e}")

def run_bot():
    """Run the Telegram bot."""
    try:
        # Create a fresh app context for the bot
        with app.app_context():
            logger.info("Starting bot within app context")
            setup_bot()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

def run_scheduler():
    """Run the scheduler."""
    try:
        # Scheduler now handles its own app context
        logger.info("Starting scheduler")
        start_scheduler()
    except Exception as e:
        logger.error(f"Scheduler error: {e}")

def check_token():
    """Check for TELEGRAM_TOKEN and validate it"""
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN environment variable is not set!")
        logger.error("The bot will not work without a valid Telegram token.")
        return None
    
    if len(token) < 20:  # Simple check for token format
        logger.error(f"TELEGRAM_TOKEN appears to be invalid (too short): {token}")
        return None
    
    logger.info(f"Found Telegram token: {token[:4]}...{token[-4:]}")
    return token

if __name__ == "__main__":
    logger.info("Starting Telegram Birthday Bot")
    
    # Check environment variables
    if not check_token():
        logger.error("Cannot start bot without a valid TELEGRAM_TOKEN.")
        logger.info("Set the TELEGRAM_TOKEN environment variable with your Telegram Bot API token.")
        logger.info("Running only the Flask app...")
        # Run only the Flask app if no token is available
        app.run(host="0.0.0.0", port=5000, debug=True)
    else:
        # We don't need to start a separate Flask app if we're using gunicorn
        # But we'll still try for development purposes
        try:
            # Start Flask app in a separate thread
            flask_thread = threading.Thread(target=run_flask_app, daemon=True)
            flask_thread.start()
            logger.info("Flask app started in background thread")
        except Exception as e:
            logger.error(f"Could not start Flask app: {e}")
        
        # Start the scheduler for birthday notifications in its own thread
        try:
            scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
            scheduler_thread.start()
            logger.info("Birthday notification scheduler started in its own thread")
        except Exception as e:
            logger.error(f"Could not start scheduler: {e}")
        
        # Give the other threads a moment to start
        time.sleep(1)
        
        # Start the bot in the main thread
        logger.info("Starting Telegram bot in main thread")
        try:
            run_bot()
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot crashed: {e}")
            raise
