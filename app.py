import os
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from sqlalchemy import func

from models import SessionLocal, User, Friend

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

# HTML template for our homepage
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Birthday Reminder Bot</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { 
            background-color: #f8f9fa; 
            padding-top: 2rem;
        }
        .stat-card {
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 1.5rem;
            transition: transform 0.3s;
        }
        .stat-card:hover {
            transform: translateY(-5px);
        }
        .stat-number {
            font-size: 2.5rem;
            font-weight: bold;
        }
        .birthday-today {
            background-color: #ffeeba;
            border-left: 4px solid #ffc107;
            padding: 1rem;
            margin-bottom: 1rem;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="row justify-content-center mb-5">
            <div class="col-md-8 text-center">
                <h1 class="display-4 mb-3">🎂 Birthday Reminder Bot</h1>
                <p class="lead">A Telegram bot that helps you remember your friends' birthdays</p>
                <div class="d-flex justify-content-center">
                    <a href="https://t.me/{{ bot_username }}" class="btn btn-primary btn-lg mt-3" target="_blank">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-telegram me-2" viewBox="0 0 16 16">
                            <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zM8.287 5.906c-.778.324-2.334.994-4.666 2.01-.378.15-.577.298-.595.442-.03.243.275.339.69.47l.175.055c.408.133.958.288 1.243.294.26.006.549-.1.868-.32 2.179-1.471 3.304-2.214 3.374-2.23.05-.012.12-.026.166.016.047.041.042.12.037.141-.03.129-1.227 1.241-1.846 1.817-.193.18-.33.307-.358.336a8.154 8.154 0 0 1-.188.186c-.38.366-.664.64.015 1.088.327.216.589.393.85.571.284.194.568.387.936.629.093.06.183.125.27.187.331.236.63.448.997.414.214-.02.435-.22.547-.82.265-1.417.786-4.486.906-5.751a1.426 1.426 0 0 0-.013-.315.337.337 0 0 0-.114-.217.526.526 0 0 0-.31-.093c-.3.005-.763.166-2.984 1.09z"/>
                        </svg>
                        Open in Telegram
                    </a>
                </div>
            </div>
        </div>

        <div class="row mb-5">
            <div class="col-md-4">
                <div class="card stat-card bg-primary text-white">
                    <div class="card-body text-center">
                        <h5 class="card-title">Total Users</h5>
                        <p class="stat-number">{{ user_count }}</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card stat-card bg-success text-white">
                    <div class="card-body text-center">
                        <h5 class="card-title">Birthdays Tracked</h5>
                        <p class="stat-number">{{ birthday_count }}</p>
                    </div>
                </div>
            </div>
            <div class="col-md-4">
                <div class="card stat-card bg-info text-white">
                    <div class="card-body text-center">
                        <h5 class="card-title">Birthdays Today</h5>
                        <p class="stat-number">{{ birthdays_today }}</p>
                    </div>
                </div>
            </div>
        </div>

        {% if today_birthdays %}
        <div class="row mb-5">
            <div class="col-md-12">
                <h3 class="mb-4">🎉 Birthdays Today</h3>
                {% for birthday in today_birthdays %}
                <div class="birthday-today">
                    <h5>{{ birthday.name }}</h5>
                    <p class="mb-0">Born on {{ birthday.birth_date.strftime('%d %B %Y') }}</p>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <div class="row">
            <div class="col-md-12">
                <div class="card">
                    <div class="card-header">
                        <h3>Features</h3>
                    </div>
                    <div class="card-body">
                        <ul class="list-group list-group-flush">
                            <li class="list-group-item">🎂 Add friends' birthdays</li>
                            <li class="list-group-item">📋 List all birthdays you're tracking</li>
                            <li class="list-group-item">🔔 Get notified on the day of birthdays</li>
                            <li class="list-group-item">🗑️ Remove birthdays you no longer want to track</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>

        <footer class="mt-5 text-center text-muted">
            <p>Birthday Reminder Bot &copy; {{ current_year }}</p>
        </footer>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

@app.route('/')
def index():
    """Status page for the bot"""
    db = SessionLocal()
    try:
        # Get stats
        user_count = db.query(func.count(User.id)).scalar() or 0
        birthday_count = db.query(func.count(Friend.id)).scalar() or 0
        
        # Get birthdays today
        today = datetime.now()
        today_month_day = (today.month, today.day)
        
        # Find birthdays that match today's month and day
        today_birthdays_query = db.query(Friend).all()
        today_birthdays = [
            friend for friend in today_birthdays_query
            if (friend.birth_date.month, friend.birth_date.day) == today_month_day
        ]
        birthdays_today = len(today_birthdays)
        
        # Render the template
        rendered_html = render_template_string(
            HTML_TEMPLATE,
            user_count=user_count,
            birthday_count=birthday_count,
            birthdays_today=birthdays_today,
            today_birthdays=today_birthdays,
            current_year=datetime.now().year,
            bot_username=os.environ.get("BOT_USERNAME", "your_birthday_bot")
        )
        
        return rendered_html
    
    finally:
        db.close()

@app.route('/api/stats')
def stats():
    """API endpoint for bot stats"""
    db = SessionLocal()
    try:
        user_count = db.query(func.count(User.id)).scalar() or 0
        birthday_count = db.query(func.count(Friend.id)).scalar() or 0
        
        return jsonify({
            "status": "success",
            "data": {
                "users": user_count,
                "birthdays": birthday_count
            }
        })
    finally:
        db.close()

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook for Telegram updates (if needed in the future)"""
    update = request.get_json()
    logger.debug(f"Received webhook update: {update}")
    return jsonify({"status": "success"})
