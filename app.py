import os
import logging
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Database setup
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize the extension with the app
db.init_app(app)

# Import models here to avoid circular imports
# Create tables if they don't exist
with app.app_context():
    # Import models after db is initialized to avoid circular imports
    from models import User, Friend
    
    # Drop and recreate all tables
    try:
        logger.info("Dropping all tables and recreating schema...")
        # Try to execute SQL directly to drop with CASCADE option if needed
        db.session.execute(db.text("DROP TABLE IF EXISTS notification_preferences CASCADE"))
        db.session.execute(db.text("DROP TABLE IF EXISTS friends CASCADE"))
        db.session.execute(db.text("DROP TABLE IF EXISTS users CASCADE"))
        db.session.commit()
        
        # Now create the tables
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        db.session.rollback()
        # If the drop fails, try just creating
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            db.session.rollback()

@app.route('/')
def index():
    """Health check endpoint"""
    return jsonify({"status": "Bot is running"})

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook for Telegram updates (if needed in the future)"""
    update = request.get_json()
    logger.debug(f"Received webhook update: {update}")
    return jsonify({"status": "success"})

@app.route('/status')
def status():
    """Display application status and user statistics"""
    with app.app_context():
        from models import User, Friend
        user_count = User.query.count()
        friend_count = Friend.query.count()
        
        # Get notification settings summary
        notification_settings = []
        for user in User.query.all():
            notification_settings.append({
                "telegram_id": user.telegram_id,
                "notification_time": user.notification_time,
                "notifications_enabled": user.notifications_enabled
            })
        
        return jsonify({
            "status": "Bot is running",
            "user_count": user_count,
            "friend_count": friend_count,
            "notification_settings": notification_settings
        })
