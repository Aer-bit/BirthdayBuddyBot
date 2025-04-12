import os
import re
import logging
from datetime import datetime
from typing import Optional

import telebot
from telebot import TeleBot
from telebot import types

from models import Friend, get_user

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

# User state constants
STATE_IDLE = "IDLE"
STATE_ADDING_FRIEND_NAME = "ADDING_FRIEND_NAME"
STATE_ADDING_FRIEND_BIRTHDAY = "ADDING_FRIEND_BIRTHDAY"

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
    
    user_data = get_user(user_id, username)
    
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
    user_data = get_user(user_id)
    
    if not user_data.friends:
        bot.reply_to(
            message,
            "You haven't added any friends yet. Use /add to add a friend."
        )
        return
    
    msg_text = "Here are your friends' birthdays:\n\n"
    
    for friend in user_data.friends.values():
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
    user_data = get_user(user_id)
    
    if not user_data.friends:
        bot.reply_to(
            message,
            "You don't have any friends to remove. Use /add to add a friend."
        )
        return
    
    keyboard = types.InlineKeyboardMarkup()
    for friend_name in user_data.friends.keys():
        keyboard.add(types.InlineKeyboardButton(
            text=friend_name, 
            callback_data=f"{DELETE_FRIEND}{friend_name}"
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
        
        # Save the friend
        user_data.friends[friend_name] = Friend(name=friend_name, birth_date=birth_date)
        
        days_until = user_data.friends[friend_name].days_until_birthday()
        next_birthday = user_data.friends[friend_name].next_birthday()
        
        bot.reply_to(
            message,
            f"Great! I've added {friend_name}'s birthday ({day}/{month}/{year}).\n\n"
            f"Their next birthday is in {days_until} days, on {next_birthday.strftime('%d/%m/%Y')}.\n\n"
            f"You'll be notified on the day of their birthday."
        )
        
        # Reset state
        user_data.state = STATE_IDLE
        user_data.temp_data = {}
        
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
    user_data = get_user(user_id)
    
    # Extract the friend name from callback data
    friend_name = call.data[len(DELETE_FRIEND):]
    
    if friend_name in user_data.friends:
        del user_data.friends[friend_name]
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

def send_birthday_notification(user_id: int, friend: Friend, days_until: int) -> None:
    """Send a birthday notification to a user."""
    if days_until == 0:
        # It's the birthday today
        message = f"🎂 Happy Birthday to {friend.name} today! 🎉"
    else:
        # This shouldn't happen, but just in case
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
        return
    
    logger.info("Starting Telegram bot...")
    bot.infinity_polling()