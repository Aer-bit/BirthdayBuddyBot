import logging
from datetime import datetime
from typing import Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse a date string in format DD/MM/YYYY.
    Returns None if parsing fails.
    """
    try:
        day, month, year = map(int, date_str.split('/'))
        return datetime(year, month, day)
    except (ValueError, TypeError) as e:
        logger.error(f"Error parsing date '{date_str}': {e}")
        return None

def format_date(date: datetime) -> str:
    """Format a datetime object as DD/MM/YYYY."""
    return date.strftime('%d/%m/%Y')

def date_to_string(date: datetime) -> str:
    """Convert a datetime to a human-readable string."""
    return date.strftime('%d %B %Y')

def get_readable_remaining_time(days: int) -> str:
    """
    Convert a number of days to a human-readable string.
    Examples: "Today", "Tomorrow", "In 5 days", "In 2 weeks"
    """
    if days == 0:
        return "Today"
    elif days == 1:
        return "Tomorrow"
    elif days < 7:
        return f"In {days} days"
    elif days == 7:
        return "In 1 week"
    elif days < 30 and days % 7 == 0:
        return f"In {days // 7} weeks"
    elif days < 30:
        weeks = days // 7
        remaining_days = days % 7
        if remaining_days == 0:
            return f"In {weeks} weeks"
        else:
            return f"In {weeks} weeks and {remaining_days} days"
    else:
        months = days // 30
        remaining_days = days % 30
        if remaining_days == 0:
            return f"In about {months} months"
        else:
            return f"In about {months} months and {remaining_days} days"

def check_valid_days_range(days: int) -> bool:
    """Check if the number of days is within a valid range (1-365)."""
    return 1 <= days <= 365
