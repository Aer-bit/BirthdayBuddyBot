import os
import logging
import time
import threading
from datetime import datetime, timedelta

from models import get_upcoming_birthdays
from bot import send_birthday_notification

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# How often to check for birthdays (in seconds)
CHECK_INTERVAL = 60 * 60  # Check every hour

def check_birthdays() -> None:
    """Check for upcoming birthdays and send notifications."""
    logger.debug("Checking for upcoming birthdays...")
    
    # Get birthdays happening today (days_ahead=0)
    today_birthdays = get_upcoming_birthdays(days_ahead=0)
    
    for user_id, birthdays in today_birthdays.items():
        for friend, days_until in birthdays:
            # Only send notifications for birthdays that are today (days_until == 0)
            if days_until == 0:
                logger.debug(f"Sending notification to user {user_id} about {friend.name}'s birthday today")
                send_birthday_notification(user_id, friend, days_until)
            
    logger.debug("Birthday check complete")

def scheduler_thread() -> None:
    """Thread function that periodically checks for birthdays."""
    logger.info("Birthday notification scheduler started")
    
    while True:
        try:
            check_birthdays()
            
            # Sleep until next check
            logger.debug(f"Sleeping for {CHECK_INTERVAL} seconds until next check")
            time.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            logger.error(f"Error in scheduler: {e}")
            # Still sleep to avoid tight loop in case of persistent errors
            time.sleep(60)

def start_scheduler() -> None:
    """Start the birthday notification scheduler in a separate thread."""
    thread = threading.Thread(target=scheduler_thread, daemon=True)
    thread.start()
    logger.info("Birthday notification scheduler thread started")