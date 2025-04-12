import os
from flask import Flask, jsonify

# Create and configure the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "birthday-reminder-secret")

# Define routes
@app.route('/')
def index():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "app": "Birthday Reminder Bot",
        "version": "1.0.0"
    })

# Add a webhook route for possible future use
@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook for Telegram updates (if needed in the future)"""
    return jsonify({
        "status": "received"
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)