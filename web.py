import os
import logging
from app import app

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Make the app available for gunicorn
application = app

if __name__ == "__main__":
    logger.info("Starting Flask web application")
    app.run(host="0.0.0.0", port=5000, debug=True)