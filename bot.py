import os
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Set

import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from models import (
    Friend, NotificationPreference, get_user, UserData, get_db_session,
    get_user_friends, add_friend, remove_friend, get_notification_preferences,
    update_notification_preferences, add_custom_notification_day, remove_custom_notification_day
)
from helpers import parse_date, format_date, check_valid_days_range

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Bot token
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# User state constants
STATE_IDLE = "IDLE"
STATE_ADDING_FRIEND_NAME = "ADDING_FRIEND_NAME"
STATE_ADDING_FRIEND_BIRTHDAY = "ADDING_FRIEND_BIRTHDAY"
STATE_ADDING_CUSTOM_DAY = "ADDING_CUSTOM_DAY"

# Callback query data identifiers
PREF_WEEK_BEFORE = "pref_week"
PREF_DAY_BEFORE = "pref_day"
PREF_ON_DAY = "pref_on_day"
PREF_CUSTOM = "pref_custom"
PREF_DONE = "pref_done"
ADD_CUSTOM_DAY = "add_custom"
REMOVE_CUSTOM_DAY = "remove_custom"
DONE_CUSTOM_DAYS = "done_custom"
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
    
    user_data = get_user(user_id, username)
    
    bot.reply_to(
        message,
        f"Hi {first_name}! I'm your Birthday Reminder Bot.\n\n"
        "I can help you keep track of your friends' birthdays and notify you "
        "before they occur.\n\n"
        "Use /add to add a friend's birthday\n"
        "Use /list to see all your friends' birthdays\n"
        "Use /notifications to set your notification preferences\n"
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
        "/notifications - Set your notification preferences\n"
        "/help - Show this help message\n"
        "/cancel - Cancel the current operation"
    )

@bot.message_handler(commands=['add'])
def add_friend(message):
    """Start the add friend conversation."""
    user_id = message.from_user.id
    user_data = get_user(user_id)
    user_data.state = STATE_ADDING_FRIEND_NAME
    user_data.temp_data = {}
    
    bot.reply_to(
        message,
        "Let's add a friend's birthday! What's your friend's name?"
    )

@bot.message_handler(commands=['list'])
def list_friends(message):
    """List all friends and their birthdays."""
    user_id = message.from_user.id
    
    # Get friends from the database
    friends = get_user_friends(user_id)
    
    if not friends:
        bot.reply_to(
            message,
            "You haven't added any friends yet. Use /add to add a friend."
        )
        return
    
    msg_text = "Here are your friends' birthdays:\n\n"
    
    for friend in friends.values():
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
    
    # Get friends from the database
    friends = get_user_friends(user_id)
    
    if not friends:
        bot.reply_to(
            message,
            "You don't have any friends to remove. Use /add to add a friend."
        )
        return
    
    keyboard = types.InlineKeyboardMarkup()
    for friend_name in friends.keys():
        keyboard.add(types.InlineKeyboardButton(
            text=friend_name, 
            callback_data=f"{DELETE_FRIEND}{friend_name}"
        ))
    
    bot.send_message(
        message.chat.id,
        "Select a friend to remove:",
        reply_markup=keyboard
    )

@bot.message_handler(commands=['notifications'])
def set_notifications(message):
    """Set notification preferences."""
    user_id = message.from_user.id
    user_data = get_user(user_id)
    
    # Create keyboard with current preferences
    pref = user_data.notification_pref
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    keyboard.add(
        types.InlineKeyboardButton(
            text=f"{'✅' if pref.week_before else '❌'} One week before",
            callback_data=PREF_WEEK_BEFORE
        ),
        types.InlineKeyboardButton(
            text=f"{'✅' if pref.day_before else '❌'} One day before",
            callback_data=PREF_DAY_BEFORE
        ),
        types.InlineKeyboardButton(
            text=f"{'✅' if pref.on_day else '❌'} On the day",
            callback_data=PREF_ON_DAY
        ),
        types.InlineKeyboardButton(
            text="Custom days...",
            callback_data=PREF_CUSTOM
        ),
        types.InlineKeyboardButton(
            text="Done",
            callback_data=PREF_DONE
        )
    )
    
    bot.send_message(
        message.chat.id,
        "Set your notification preferences:",
        reply_markup=keyboard
    )

@bot.message_handler(commands=['cancel'])
def cancel(message):
    """Cancel the current operation."""
    user_id = message.from_user.id
    user_data = get_user(user_id)
    
    if user_data.state == STATE_IDLE:
        bot.reply_to(message, "No active operation to cancel.")
        return
    
    user_data.state = STATE_IDLE
    user_data.temp_data = {}
    
    bot.reply_to(message, "Operation cancelled.")

# Handle message text based on state
@bot.message_handler(func=lambda message: True, content_types=['text'])
def handle_text(message):
    """Handle text messages based on the user's current state."""
    user_id = message.from_user.id
    user_data = get_user(user_id)
    
    if user_data.state == STATE_ADDING_FRIEND_NAME:
        save_friend_name(message, user_data)
    elif user_data.state == STATE_ADDING_FRIEND_BIRTHDAY:
        save_friend_birthday(message, user_data)
    elif user_data.state == STATE_ADDING_CUSTOM_DAY:
        save_custom_day(message, user_data)
    else:
        bot.reply_to(
            message,
            "I'm not sure what you want to do. Please use a command like /help to see available options."
        )

# Friend addition helpers
def save_friend_name(message, user_data):
    """Save the friend's name and ask for birthday."""
    friend_name = message.text.strip()
    
    # Check if name is valid
    if not friend_name or len(friend_name) > 100:
        bot.reply_to(
            message,
            "Please enter a valid name (not empty and less than 100 characters)."
        )
        return
    
    user_data.temp_data["friend_name"] = friend_name
    user_data.state = STATE_ADDING_FRIEND_BIRTHDAY
    
    bot.reply_to(
        message,
        f"When is {friend_name}'s birthday? Please enter the date in DD/MM/YYYY format.\n"
        "For example: 15/06/1990"
    )

def save_friend_birthday(message, user_data):
    """Save the friend's birthday."""
    birthday_text = message.text.strip()
    
    # Parse the birthday
    try:
        # Check if the format is correct
        if not re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', birthday_text):
            raise ValueError("Format doesn't match DD/MM/YYYY")
        
        day, month, year = map(int, birthday_text.split('/'))
        birth_date = datetime(year, month, day)
        
        friend_name = user_data.temp_data["friend_name"]
        
        # Save the friend to the database
        friend = add_friend(user_data.user_id, friend_name, birth_date)
        
        days_until = friend.days_until_birthday()
        next_birthday = friend.next_birthday()
        
        bot.reply_to(
            message,
            f"Great! I've added {friend_name}'s birthday ({day}/{month}/{year}).\n\n"
            f"Their next birthday is in {days_until} days, on {next_birthday.strftime('%d/%m/%Y')}."
        )
        
        # Reset state
        user_data.state = STATE_IDLE
        user_data.temp_data = {}
        
        # Save user state to database
        session = get_db_session()
        try:
            user_data.save(session)
        finally:
            session.close()
        
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
    
    # Try to remove the friend from the database
    if remove_friend(user_id, friend_name):
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

@bot.callback_query_handler(func=lambda call: call.data in [PREF_WEEK_BEFORE, PREF_DAY_BEFORE, PREF_ON_DAY, PREF_DONE])
def handle_preference_callback(call):
    """Handle preference setting callbacks."""
    user_id = call.from_user.id
    user_data = get_user(user_id)
    pref = get_notification_preferences(user_id)
    
    if call.data == PREF_WEEK_BEFORE:
        # Toggle the week_before preference
        update_notification_preferences(user_id, week_before=not pref.week_before)
        update_notification_keyboard(call, user_data)
        
    elif call.data == PREF_DAY_BEFORE:
        # Toggle the day_before preference
        update_notification_preferences(user_id, day_before=not pref.day_before)
        update_notification_keyboard(call, user_data)
        
    elif call.data == PREF_ON_DAY:
        # Toggle the on_day preference
        update_notification_preferences(user_id, on_day=not pref.on_day)
        update_notification_keyboard(call, user_data)
        
    elif call.data == PREF_DONE:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="Notification preferences updated!"
        )
    
    bot.answer_callback_query(call.id)

def update_notification_keyboard(call, user_data):
    """Update the notification preferences keyboard."""
    # Get current preferences from database
    pref = get_notification_preferences(user_data.user_id)
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(
            text=f"{'✅' if pref.week_before else '❌'} One week before",
            callback_data=PREF_WEEK_BEFORE
        ),
        types.InlineKeyboardButton(
            text=f"{'✅' if pref.day_before else '❌'} One day before",
            callback_data=PREF_DAY_BEFORE
        ),
        types.InlineKeyboardButton(
            text=f"{'✅' if pref.on_day else '❌'} On the day",
            callback_data=PREF_ON_DAY
        ),
        types.InlineKeyboardButton(
            text="Custom days...",
            callback_data=PREF_CUSTOM
        ),
        types.InlineKeyboardButton(
            text="Done",
            callback_data=PREF_DONE
        )
    )
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Set your notification preferences:",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == PREF_CUSTOM)
def handle_custom_days(call):
    """Handle custom days settings."""
    user_id = call.from_user.id
    user_data = get_user(user_id)
    
    show_custom_days(call, user_data)
    bot.answer_callback_query(call.id)

def show_custom_days(call, user_data):
    """Show the custom days interface."""
    # Get notification preferences from database
    pref = get_notification_preferences(user_data.user_id)
    
    # Display current custom days
    custom_days = pref.get_custom_days()
    custom_days_text = "No custom days set" if not custom_days else \
                       ", ".join(str(day) for day in sorted(custom_days))
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(types.InlineKeyboardButton(
        text="Add custom day",
        callback_data=ADD_CUSTOM_DAY
    ))
    
    # Add remove buttons if there are custom days
    if custom_days:
        keyboard.add(types.InlineKeyboardButton(
            text="Remove custom day",
            callback_data=REMOVE_CUSTOM_DAY
        ))
    
    keyboard.add(types.InlineKeyboardButton(
        text="Back to preferences",
        callback_data=DONE_CUSTOM_DAYS
    ))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"Custom days before birthday to notify:\n{custom_days_text}\n\n"
             "Choose an option:",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == ADD_CUSTOM_DAY)
def handle_add_custom_day(call):
    """Handle add custom day button."""
    user_id = call.from_user.id
    user_data = get_user(user_id)
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Enter the number of days before the birthday when you want to be notified.\n"
             "For example, enter '3' to be notified 3 days before."
    )
    
    user_data.state = STATE_ADDING_CUSTOM_DAY
    user_data.temp_data["message_id"] = call.message.message_id
    
    bot.answer_callback_query(call.id)

def save_custom_day(message, user_data):
    """Save the custom notification day."""
    try:
        day = int(message.text.strip())
        
        if not check_valid_days_range(day):
            bot.reply_to(
                message,
                "Please enter a positive number of days between 1 and 365."
            )
            return
        
        # Add the custom day to the database
        custom_days = add_custom_notification_day(user_data.user_id, day)
        
        # Show confirmation
        custom_days_str = ", ".join(str(d) for d in sorted(custom_days))
        
        bot.reply_to(
            message,
            f"Custom notification added for {day} days before.\n\n"
            f"Your custom notification days: {custom_days_str}\n\n"
            "Use /notifications to continue setting your preferences."
        )
        
        # Try to update the previous message if it exists
        if "message_id" in user_data.temp_data:
            try:
                # Try to show the updated custom days list
                call = types.CallbackQuery(
                    id="",
                    from_user=message.from_user,
                    message=types.Message(
                        message_id=user_data.temp_data["message_id"],
                        chat=message.chat,
                        content_type="text",
                        text="",
                        date=0,
                        from_user=None,
                        options={}
                    ),
                    chat_instance="",
                    data=None,
                    game_short_name=None,
                    json_string=""
                )
                show_custom_days(call, user_data)
            except Exception as e:
                logger.error(f"Error updating message: {e}")
        
        # Reset state
        user_data.state = STATE_IDLE
        user_data.temp_data = {}
        
        # Save user state to database
        session = get_db_session()
        try:
            user_data.save(session)
        finally:
            session.close()
        
    except ValueError:
        bot.reply_to(
            message,
            "Please enter a valid number of days."
        )

@bot.callback_query_handler(func=lambda call: call.data == REMOVE_CUSTOM_DAY)
def handle_remove_custom_day(call):
    """Handle remove custom day button."""
    user_id = call.from_user.id
    user_data = get_user(user_id)
    
    # Get notification preferences from database
    pref = get_notification_preferences(user_id)
    custom_days = pref.get_custom_days()
    
    # Show list of days to remove
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    
    for day in sorted(custom_days):
        keyboard.add(types.InlineKeyboardButton(
            text=f"{day} days before",
            callback_data=f"remove_day_{day}"
        ))
    
    keyboard.add(types.InlineKeyboardButton(
        text="Back",
        callback_data="back_to_custom"
    ))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Select a custom day to remove:",
        reply_markup=keyboard
    )
    
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("remove_day_"))
def handle_remove_specific_day(call):
    """Handle removing a specific custom day."""
    user_id = call.from_user.id
    user_data = get_user(user_id)
    
    # Remove the selected day from the database
    day = int(call.data.split("_")[-1])
    remove_custom_notification_day(user_id, day)
    
    show_custom_days(call, user_data)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "back_to_custom")
def handle_back_to_custom(call):
    """Handle back button in custom days menu."""
    user_id = call.from_user.id
    user_data = get_user(user_id)
    
    show_custom_days(call, user_data)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == DONE_CUSTOM_DAYS)
def handle_done_custom_days(call):
    """Handle done button in custom days menu."""
    user_id = call.from_user.id
    user_data = get_user(user_id)
    
    update_notification_keyboard(call, user_data)
    bot.answer_callback_query(call.id)

def send_birthday_notification(user_id: int, friend: Friend, days_until: int) -> None:
    """Send a birthday notification to a user."""
    if not bot:
        logger.error("Bot not initialized. Cannot send notification.")
        return
        
    try:
        if days_until == 0:
            message = f"🎉 Today is {friend.name}'s birthday! 🎂"
        elif days_until == 1:
            message = f"🔔 Reminder: Tomorrow is {friend.name}'s birthday! 🎁"
        elif days_until == 7:
            message = f"📆 Heads up! {friend.name}'s birthday is in one week, on {friend.next_birthday().strftime('%d/%m/%Y')}."
        else:
            message = f"📅 {friend.name}'s birthday is in {days_until} days, on {friend.next_birthday().strftime('%d/%m/%Y')}."
        
        bot.send_message(chat_id=user_id, text=message)
        logger.info(f"Sent birthday notification to user {user_id} about {friend.name}")
        
    except Exception as e:
        logger.error(f"Failed to send notification to user {user_id}: {e}")

def setup_bot():
    """Initialize and start the bot."""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN not found in environment variables!")
        raise ValueError("TELEGRAM_TOKEN is not set")
        
    logger.info("Starting Telegram bot...")
    
    # Start the bot polling in a separate thread
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
    
    return bot