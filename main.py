import os
import logging
import threading
import time
from app import app
from bot import setup_bot
from scheduler import start_scheduler

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
            raise

def run_bot():
    """Run the Telegram bot."""
    # Create a fresh app context for the bot
    with app.app_context():
        setup_bot()

def run_scheduler():
    """Run the scheduler."""
    # Scheduler now handles its own app context
    start_scheduler()

if __name__ == "__main__":
    logger.info("Starting Telegram Birthday Bot")
    
    # Check if we have a Telegram token
    if not os.environ.get("TELEGRAM_TOKEN"):
        logger.error("TELEGRAM_TOKEN environment variable is not set. The bot will not work properly.")
        logger.info("Set the TELEGRAM_TOKEN environment variable with your Telegram Bot API token")
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
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("Birthday notification scheduler started in its own thread")
        
        # Give the other threads a moment to start
        time.sleep(1)
        
        # Start the bot in the main thread
        logger.info("Starting Telegram bot in main thread")
        run_bot()
