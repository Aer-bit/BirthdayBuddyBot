import logging
from app import app as application

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

logger.info("Starting Flask web application")

if __name__ == "__main__":
    application.run(host="0.0.0.0", port=5000, debug=True)