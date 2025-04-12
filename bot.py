import os
import re
import logging
import sys
from datetime import datetime
from typing import Optional, Dict, Tuple

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('telegram_bot.log')
    ]
)
logger = logging.getLogger(__name__)

try:
    import telebot
    from telebot import TeleBot, apihelper
    from telebot import types
    logger.info("Successfully imported telebot modules")
except Exception as e:
    logger.error(f"Error importing telebot modules: {e}")
    raise

try:
    from models import (
        get_user, 
        get_user_friends, 
        save_friend, 
        delete_friend, 
        update_user_state, 
        get_user_state,
        STATE_IDLE,
        STATE_ADDING_FRIEND_NAME,
        STATE_ADDING_FRIEND_BIRTHDAY
    )
    # Import Flask app for context
    from app import app as flask_app
    
    # Create a helper function to run database operations with app context
    def with_app_context(func):
        """Run a database function within the app context."""
        def wrapper(*args, **kwargs):
            try:
                with flask_app.app_context():
                    logger.debug(f"Running {func.__name__} within app context")
                    return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                return None
        return wrapper
    
    # Apply app context to all database functions
    get_user_with_context = with_app_context(get_user)
    get_user_friends_with_context = with_app_context(get_user_friends)
    save_friend_with_context = with_app_context(save_friend)
    delete_friend_with_context = with_app_context(delete_friend)
    update_user_state_with_context = with_app_context(update_user_state)
    get_user_state_with_context = with_app_context(get_user_state)
    
    logger.info("Successfully imported models and set up context wrappers")
except Exception as e:
    logger.error(f"Error importing models: {e}")
    raise

# Bot token
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# Enable middleware for better error handling
apihelper.ENABLE_MIDDLEWARE = True

# Callback query data identifiers
DELETE_FRIEND = "delete_friend_"

# Create bot instance
bot = telebot.TeleBot(TELEGRAM_TOKEN) if TELEGRAM_TOKEN else None

# Command handlers
@bot.message_handler(commands=['start'])
def start(message):
    """Send a welcome message when the command /start is issued."""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Create or get user in the database using wrapped function
    get_user_with_context(user_id, username)
    logger.debug(f"Created or retrieved user: {user_id}, {username}")
    
    bot.reply_to(
        message,
        f"Hi {first_name}! I'm your Birthday Reminder Bot.\n\n"
        "I can help you keep track of your friends' birthdays and notify you "
        "on the day of their birthday.\n\n"
        "Use /add to add a friend's birthday\n"
        "Use /list to see all your friends' birthdays\n"
        "Use /help to see all available commands"
    )

@bot.message_handler(commands=['help'])
def help_command(message):
    """Send a help message when the command /help is issued."""
    bot.reply_to(
        message,
        "Here are the commands you can use:\n\n"
        "/start - Start the bot\n"
        "/add - Add a friend's birthday\n"
        "/list - List all your friends' birthdays\n"
        "/remove - Remove a friend from your list\n"
        "/help - Show this help message\n"
        "/cancel - Cancel the current operation"
    )

@bot.message_handler(commands=['add'])
def add_friend(message):
    """Start the add friend conversation."""
    user_id = message.from_user.id
    
    # Update user state in the database using wrapped function
    update_user_state_with_context(user_id, STATE_ADDING_FRIEND_NAME, {})
    
    bot.reply_to(
        message,
        "Let's add a friend's birthday! What's your friend's name?"
    )

@bot.message_handler(commands=['list'])
def list_friends(message):
    """List all friends and their birthdays."""
    user_id = message.from_user.id
    friends = get_user_friends_with_context(user_id)
    
    if not friends:
        bot.reply_to(
            message,
            "You haven't added any friends yet. Use /add to add a friend."
        )
        return
    
    msg_text = "Here are your friends' birthdays:\n\n"
    
    for friend in friends:
        days_until = friend.days_until_birthday()
        next_birthday = friend.next_birthday()
        birth_date = friend.birth_date
        
        msg_text += f"🎂 {friend.name}: {birth_date.strftime('%d/%m/%Y')}\n"
        msg_text += f"   Next birthday: {next_birthday.strftime('%d/%m/%Y')} ({days_until} days away)\n\n"
    
    bot.reply_to(message, msg_text)

@bot.message_handler(commands=['remove'])
def remove_friend(message):
    """Send a list of friends to remove."""
    user_id = message.from_user.id
    friends = get_user_friends_with_context(user_id)
    
    if not friends:
        bot.reply_to(
            message,
            "You don't have any friends to remove. Use /add to add a friend."
        )
        return
    
    keyboard = types.InlineKeyboardMarkup()
    for friend in friends:
        keyboard.add(types.InlineKeyboardButton(
            text=friend.name, 
            callback_data=f"{DELETE_FRIEND}{friend.name}"
        ))
    
    bot.send_message(
        message.chat.id,
        "Select a friend to remove:",
        reply_markup=keyboard
    )

@bot.message_handler(commands=['cancel'])
def cancel(message):
    """Cancel the current operation."""
    user_id = message.from_user.id
    state, _ = get_user_state_with_context(user_id)
    
    if state == STATE_IDLE:
        bot.reply_to(message, "No active operation to cancel.")
        return
    
    update_user_state_with_context(user_id, STATE_IDLE, {})
    
    bot.reply_to(message, "Operation cancelled.")

# Handle message text based on state
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text(message):
    """Handle text messages based on the user's current state."""
    user_id = message.from_user.id
    state, temp_data = get_user_state_with_context(user_id)
    
    if state == STATE_ADDING_FRIEND_NAME:
        save_friend_name(message, user_id, temp_data)
    elif state == STATE_ADDING_FRIEND_BIRTHDAY:
        save_friend_birthday(message, user_id, temp_data)
    else:
        bot.reply_to(
            message,
            "I'm not sure what you want to do. Please use a command like /help to see available options."
        )

# Friend addition helpers
def save_friend_name(message, user_id, temp_data):
    """Save the friend's name and ask for birthday."""
    friend_name = message.text.strip()
    
    # Check if name is valid
    if not friend_name or len(friend_name) > 100:
        bot.reply_to(
            message,
            "Please enter a valid name (not empty and less than 100 characters)."
        )
        return
    
    # Update the temp_data with the friend's name and change the state
    temp_data["friend_name"] = friend_name
    update_user_state_with_context(user_id, STATE_ADDING_FRIEND_BIRTHDAY, temp_data)
    
    bot.reply_to(
        message,
        f"When is {friend_name}'s birthday? Please enter the date in DD/MM/YYYY format.\n"
        "For example: 15/06/1990"
    )

def save_friend_birthday(message, user_id, temp_data):
    """Save the friend's birthday."""
    birthday_text = message.text.strip()
    
    # Parse the birthday
    try:
        # Check if the format is correct
        if not re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', birthday_text):
            raise ValueError("Format doesn't match DD/MM/YYYY")
        
        day, month, year = map(int, birthday_text.split('/'))
        birth_date = datetime(year, month, day)
        
        friend_name = temp_data.get("friend_name")
        if not friend_name:
            bot.reply_to(
                message,
                "Sorry, there was an error processing your request. Please try adding a friend again."
            )
            update_user_state_with_context(user_id, STATE_IDLE, {})
            return
        
        # Save the friend to database using context-aware function
        friend = save_friend_with_context(user_id, friend_name, birth_date)
        
        if not friend:
            bot.reply_to(
                message,
                "Sorry, there was an error saving your friend. Please try again."
            )
            update_user_state_with_context(user_id, STATE_IDLE, {})
            return
        
        days_until = friend.days_until_birthday()
        next_birthday = friend.next_birthday()
        
        bot.reply_to(
            message,
            f"Great! I've added {friend_name}'s birthday ({day}/{month}/{year}).\n\n"
            f"Their next birthday is in {days_until} days, on {next_birthday.strftime('%d/%m/%Y')}.\n\n"
            f"You'll be notified on the day of their birthday."
        )
        
        # Reset state with context-aware function
        update_user_state_with_context(user_id, STATE_IDLE, {})
        
    except (ValueError, IndexError) as e:
        logger.error(f"Error parsing birthday: {e}")
        bot.reply_to(
            message,
            "I couldn't understand that date format. Please enter the date as DD/MM/YYYY.\n"
            "For example: 15/06/1990"
        )

# Callback query handlers
@bot.callback_query_handler(func=lambda call: call.data.startswith(DELETE_FRIEND))
def handle_delete_friend_callback(call):
    """Handle friend deletion callbacks."""
    user_id = call.from_user.id
    
    # Extract the friend name from callback data
    friend_name = call.data[len(DELETE_FRIEND):]
    
    # Delete the friend from database using context-aware function
    deleted = delete_friend_with_context(user_id, friend_name)
    
    if deleted:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"Removed {friend_name} from your friends list."
        )
    else:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Friend not found. They may have been already removed."
        )
    
    bot.answer_callback_query(call.id)

def send_birthday_notification(user_id: int, friend, days_until: int) -> None:
    """Send a birthday notification to a user."""
    if days_until == 0:
        # It's the birthday today
        message = f"🎂 Happy Birthday to {friend.name} today! 🎉"
    else:
        # This shouldn't happen since we only notify on the actual birthday
        message = f"🎂 {friend.name}'s birthday is in {days_until} days."
        
    try:
        bot.send_message(user_id, message)
        logger.info(f"Sent birthday notification to user {user_id} for {friend.name}")
    except Exception as e:
        logger.error(f"Error sending notification to user {user_id}: {e}")

def setup_bot():
    """Initialize and start the bot."""
    if not bot:
        logger.error("Telegram bot not initialized. TELEGRAM_TOKEN may be missing.")
        logger.error(f"TELEGRAM_TOKEN value: {TELEGRAM_TOKEN}")
        logger.error("Please make sure you have set the TELEGRAM_TOKEN environment variable.")
        return
    
    # Note: We'll be in an app context when this is called from main.py
    logger.info(f"Setting up bot with token: {TELEGRAM_TOKEN[:4]}...{TELEGRAM_TOKEN[-4:]}")
    
    try:
        # Setup webhook mode or polling
        logger.info("Bot is being set up in polling mode")
        
        # Register error handler for better debugging
        def handle_errors(update_json, exception_instance):
            logger.error(f"Telegram bot error with update {update_json}: {exception_instance}")
        
        # Improved debugging - check the bot's getMe() method to verify token
        try:
            bot_info = bot.get_me()
            logger.info(f"Bot connected successfully! Bot username: @{bot_info.username}")
        except Exception as e:
            logger.error(f"Failed to get bot info: {e}")
            return
        
        # Enable middleware with specific handler
        apihelper.ENABLE_MIDDLEWARE = True
        bot.middleware_handler(handle_errors)
        
        # Add a custom update handler to verify processing
        @bot.message_handler(func=lambda message: True, content_types=['text'])
        def echo_message(message):
            logger.debug(f"Received message: {message.text}")
            if message.text == '/ping':
                bot.reply_to(message, 'Pong! The bot is working correctly.')
        
        logger.info("Starting Telegram bot with infinity polling...")
        bot.infinity_polling(timeout=20, long_polling_timeout=20)
    except Exception as e:
        logger.error(f"Failed to start the bot: {e}")
        raise