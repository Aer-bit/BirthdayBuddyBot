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
    # Detect how this script was launched
    import psutil
    is_telegram_bot = False
    
    # Get process info
    current_process = psutil.Process()
    parent_process = current_process.parent()
    current_pid = current_process.pid
    
    # Get command line used to start this process
    try:
        cmdline = current_process.cmdline()
        parent_cmdline = parent_process.cmdline() if parent_process else []
        logger.debug(f"Process cmdline: {cmdline}")
        logger.debug(f"Parent cmdline: {parent_cmdline}")
        
        # Check if we're running under gunicorn (this would be the Flask app)
        if any('gunicorn' in cmd for cmd in parent_cmdline):
            is_telegram_bot = False
            logger.info(f"Running under gunicorn as Flask app (PID: {current_pid})")
        # If we're running as a direct Python process (not under gunicorn), this is the bot
        elif 'python' in cmdline[0]:
            is_telegram_bot = True
            logger.info(f"Running as direct Python process - will be Telegram bot (PID: {current_pid})")
    except Exception as e:
        logger.error(f"Error detecting process type: {e}")
        # Default to running Flask if we can't detect
        is_telegram_bot = False
    
    # Check which workflow we're running in
    if "telegram_bot" in workflow_name.lower():
        # In the telegram_bot workflow, only run the bot if TELEGRAM_TOKEN is available
        if not os.environ.get("TELEGRAM_TOKEN"):
            logger.error("TELEGRAM_TOKEN environment variable is not set. The bot will not work properly.")
            logger.info("Set the TELEGRAM_TOKEN environment variable with your Telegram Bot API token")
            sys.exit(1)
        else:
            # Start the scheduler for birthday notifications
            start_scheduler()
            logger.info("Running Telegram bot in telegram_bot workflow")
            run_bot()
    else:
        # In any other workflow (like Start application), only run the Flask app
        logger.info("Running Flask app in Start application workflow")
        app.run(host="0.0.0.0", port=5000, debug=False)
