import os
import logging
from bot import setup_bot
from scheduler import start_scheduler

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_bot():
    """Run the Telegram bot."""
    setup_bot()

if __name__ == "__main__":
    logger.info("Starting Telegram Birthday Bot")
    
    # Check if we have a Telegram token
    if not os.environ.get("TELEGRAM_TOKEN"):
        logger.error("TELEGRAM_TOKEN environment variable is not set. The bot will not work properly.")
        logger.info("Set the TELEGRAM_TOKEN environment variable with your Telegram Bot API token")
    else:
        # Start the scheduler for birthday notifications
        start_scheduler()
        
        # Start the bot in the main thread
        logger.info("Starting Telegram bot in main thread")
        run_bot()
