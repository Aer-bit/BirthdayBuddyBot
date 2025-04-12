import logging
from functools import wraps
from typing import Callable, Any

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def with_app_context(func: Callable) -> Callable:
    """
    Decorator to run a database function within the Flask app context.
    This avoids circular imports by importing app at runtime.
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        from app import app
        with app.app_context():
            logger.debug(f"Running {func.__name__} within app context")
            return func(*args, **kwargs)
    return wrapper