import os
import logging
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key")

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
