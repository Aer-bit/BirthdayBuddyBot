import os
import logging
import threading
import sys
from app import app
from bot import setup_bot
from scheduler import start_scheduler

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_flask_app():
    """Run the Flask app in a separate thread."""
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

def run_bot():
    """Run the Telegram bot."""
    setup_bot()

if __name__ == "__main__":
    # Check which workflow we're in based on command-line arguments or environment
    is_telegram_bot = False
    
    # Check command line arguments
    if len(sys.argv) > 1 and "telegram_bot" in sys.argv[1].lower():
        is_telegram_bot = True
    
    # Check which workflow is currently running
    workflow_name = os.environ.get("REPL_WORKFLOW", "unknown")
    logger.info(f"Starting in workflow: {workflow_name}")
    
    # If workflow name contains telegram_bot, mark it as the bot workflow
    if "telegram_bot" in workflow_name.lower():
        is_telegram_bot = True
    
    # Check if we have a Telegram token
    if not os.environ.get("TELEGRAM_TOKEN"):
        logger.error("TELEGRAM_TOKEN environment variable is not set. The bot will not work properly.")
        logger.info("Set the TELEGRAM_TOKEN environment variable with your Telegram Bot API token")
        logger.info("Running only the Flask app...")
        # Run only the Flask app if no token is available
        app.run(host="0.0.0.0", port=5000, debug=True)
    else:
        # Start the scheduler for birthday notifications
        start_scheduler()
        
        # Check which workflow is running and act accordingly
        if is_telegram_bot:
            # If this is the telegram_bot workflow, only run the bot
            logger.info("Running Telegram bot in telegram_bot workflow")
            run_bot()
        else:
            # If this is any other workflow (like Start application), only run the Flask app
            logger.info("Running Flask app in Start application workflow")
            app.run(host="0.0.0.0", port=5000, debug=False)
