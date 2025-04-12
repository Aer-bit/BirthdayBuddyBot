import os
import logging
import threading
from app import app
from bot import setup_bot
from scheduler import start_scheduler

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create a Flask app context for the bot and scheduler threads
app_context = app.app_context()

def run_flask_app():
    """Run the Flask app in a separate thread."""
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

def run_bot():
    """Run the Telegram bot."""
    # Push the app context in this thread
    app_context.push()
    setup_bot()

def run_scheduler():
    """Run the scheduler in the app context."""
    # Push the app context in this thread
    app_context.push()
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
        # Start the scheduler for birthday notifications in its own thread
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        logger.info("Birthday notification scheduler started in its own thread")
        
        # Start Flask app in a separate thread
        flask_thread = threading.Thread(target=run_flask_app, daemon=True)
        flask_thread.start()
        logger.info("Flask app started in background thread")
        
        # Start the bot in the main thread
        logger.info("Starting Telegram bot in main thread")
        run_bot()
