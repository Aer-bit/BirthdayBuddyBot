import os
import logging
import time
import threading
from datetime import datetime, timedelta

from app import app
from models import get_upcoming_birthdays_with_context, get_all_users_with_context
from bot import send_birthday_notification

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# How often to check for birthdays (in seconds)
CHECK_INTERVAL = 60 * 5  # Check every 5 minutes to respect user notification times

def check_birthdays(app_context) -> None:
    """Check for upcoming birthdays and send notifications based on user preferences."""
    current_time = datetime.now()
    current_hour = current_time.hour
    current_minute = current_time.minute
    
    logger.debug(f"Checking for birthdays at {current_time.strftime('%H:%M')}...")
    
    # Ensure we're in an application context
    with app_context:
        # Get all users to check their notification preferences
        all_users = get_all_users_with_context()
        
        # For each user with notifications enabled, check if it's their preferred notification time
        for user in all_users:
            # Skip users who have disabled notifications
            if not user.notifications_enabled:
                logger.debug(f"Skipping user {user.telegram_id} - notifications disabled")
                continue
            
            # Get the user's preferred notification hour and minute
            pref_hour, pref_minute = user.get_notification_hour_minute()
            
            # Check if it's time to send notifications for this user
            # Allow for some delay (within 5 minutes of preferred time)
            time_diff_minutes = abs((current_hour * 60 + current_minute) - (pref_hour * 60 + pref_minute))
            
            if time_diff_minutes <= 5:  # Within 5 minutes of user's preferred time
                logger.debug(f"Checking birthdays for user {user.telegram_id} (preferred time: {user.notification_time})")
                
                # Get birthdays that happen today (days_ahead=0) for all users
                # We filter for this specific user below
                today_birthdays = get_upcoming_birthdays_with_context(days_ahead=0)
                
                # Check if this user has any birthday notifications
                if user.telegram_id in today_birthdays:
                    for friend, days_until in today_birthdays[user.telegram_id]:
                        logger.debug(f"Sending notification to user {user.telegram_id} about {friend.name}'s birthday today")
                        # Send the notification directly (telebot is synchronous)
                        send_birthday_notification(user.telegram_id, friend, days_until)
            else:
                logger.debug(f"Not notification time for user {user.telegram_id} - current: {current_hour}:{current_minute}, preferred: {pref_hour}:{pref_minute}")
    
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
