import os
import logging
import time
import threading
from datetime import datetime, timedelta

from app import app
from models import get_upcoming_birthdays
from bot import send_birthday_notification

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# How often to check for birthdays (in seconds)
CHECK_INTERVAL = 60 * 60  # Check every hour

def check_birthdays(app_context) -> None:
    """Check for upcoming birthdays and send notifications."""
    logger.debug("Checking for upcoming birthdays...")
    
    # Ensure we're in an application context
    with app_context:
        # Get birthdays that happen today (days_ahead=0)
        today_birthdays = get_upcoming_birthdays(days_ahead=0)
        
        for user_id, birthdays in today_birthdays.items():
            for friend, days_until in birthdays:
                logger.debug(f"Sending notification to user {user_id} about {friend.name}'s birthday today")
                # Send the notification directly (telebot is synchronous)
                send_birthday_notification(user_id, friend, days_until)
    
    logger.debug("Birthday check complete")

def scheduler_thread(app_context) -> None:
    """Thread function that periodically checks for birthdays."""
    logger.info("Birthday notification scheduler started")
    
    while True:
        try:
            check_birthdays(app_context)
            
            # Sleep until next check
            logger.debug(f"Sleeping for {CHECK_INTERVAL} seconds until next check")
            time.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"Error in scheduler: {e}")
            # Still sleep to avoid tight loop in case of persistent errors
            time.sleep(60)

def start_scheduler() -> None:
    """Start the birthday notification scheduler in a separate thread."""
    # Create a new application context
    app_context = app.app_context()
    
    thread = threading.Thread(target=scheduler_thread, args=(app_context,), daemon=True)
    thread.start()
    logger.info("Birthday notification scheduler thread started")
