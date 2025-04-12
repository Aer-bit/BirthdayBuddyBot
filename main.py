import os
import logging
import threading
import sys
import psutil

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Detect how this script was launched
is_telegram_bot = False

def is_running_as_bot():
    """Determine if we're running as the Telegram bot or as the Flask app."""
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
            logger.info(f"Running under gunicorn as Flask app (PID: {current_pid})")
            return False
        # If we're running as a direct Python process (not under gunicorn), this is the bot
        elif 'python' in cmdline[0]:
            logger.info(f"Running as direct Python process - will be Telegram bot (PID: {current_pid})")
            return True
    except Exception as e:
        logger.error(f"Error detecting process type: {e}")
    
    # Default to running Flask if we can't detect
    return False

# Flask application import - handled this way to avoid circular imports
def setup_flask():
    """Import and set up Flask app."""
    from app import app
    return app

# Bot setup - only imported if we're running as the bot
def setup_telegram_bot():
    """Import and set up the Telegram bot."""
    from bot import setup_bot
    from scheduler import start_scheduler
    
    # Check for required environment variables
    if not os.environ.get("TELEGRAM_TOKEN"):
        logger.error("TELEGRAM_TOKEN environment variable is not set. The bot will not work properly.")
        logger.info("Set the TELEGRAM_TOKEN environment variable with your Telegram Bot API token")
        sys.exit(1)
    
    # Start the scheduler for birthday notifications
    start_scheduler()
    
    # Start the bot
    logger.info("Running Telegram bot")
    return setup_bot()

if __name__ == "__main__":
    # Determine which mode to run in
    is_telegram_bot = is_running_as_bot()
    
    if is_telegram_bot:
        # Run as Telegram bot
        bot = setup_telegram_bot()
    else:
        # Run as Flask app
        app = setup_flask()
        app.run(host="0.0.0.0", port=5000, debug=False)
else:
    # When imported by gunicorn, set up the Flask app
    app = setup_flask()