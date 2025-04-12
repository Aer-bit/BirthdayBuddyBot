
# Telegram Birthday Bot

A Telegram bot that helps users keep track of their friends' birthdays and sends notifications on the special day.

## Prerequisites

- Python 3.11 or higher
- PostgreSQL database
- Telegram Bot Token (get it from [@BotFather](https://t.me/botfather))

## Required Python Packages

The following packages are required:
```
email-validator>=2.2.0
flask>=3.1.0
flask-sqlalchemy>=3.1.1
gunicorn>=23.0.0
psycopg2-binary>=2.9.10
pytelegrambotapi>=4.26.0
python-telegram-bot>=22.0
scheduler>=0.8.8
sqlalchemy>=2.0.40
telegram>=0.0.1
tlgbotfwk>=0.4.61
```

## Environment Setup

1. Set your Telegram Bot Token as an environment variable:
```bash
export TELEGRAM_TOKEN="your_bot_token_here"
```

## Running the Bot

The application consists of two main components:
1. A Flask web application (running on port 5000)
2. The Telegram bot itself

To start both components, run:
```bash
python main.py
```

This will:
- Start the Flask web application on http://0.0.0.0:5000
- Initialize the database tables
- Start the Telegram bot
- Begin the birthday notification scheduler

## Features

- Add friends and their birthdays
- Get notifications on friends' birthdays
- Customize notification time
- Enable/disable notifications
- List all saved birthdays
- Delete friends from the birthday list

## Bot Commands

- `/start` - Initialize the bot
- `/help` - Show available commands
- `/addfriend` - Add a new friend's birthday
- `/listfriends` - Show all saved birthdays
- `/settings` - Manage notification preferences
