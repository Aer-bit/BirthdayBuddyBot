import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@dataclass
class Friend:
    """Class representing a friend's birthday information"""
    name: str
    birth_date: datetime
    
    def days_until_birthday(self) -> int:
        """Calculate days until next birthday"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        next_birthday = datetime(today.year, self.birth_date.month, self.birth_date.day)
        
        # If birthday has already occurred this year, calculate for next year
        if next_birthday < today:
            next_birthday = datetime(today.year + 1, self.birth_date.month, self.birth_date.day)
        
        return (next_birthday - today).days
    
    def next_birthday(self) -> datetime:
        """Get the date of the next birthday"""
        today = datetime.now()
        next_birthday = datetime(today.year, self.birth_date.month, self.birth_date.day)
        
        # If birthday has already occurred this year, calculate for next year
        if next_birthday < today:
            next_birthday = datetime(today.year + 1, self.birth_date.month, self.birth_date.day)
            
        return next_birthday

@dataclass
class NotificationPreference:
    """Class representing notification preferences"""
    week_before: bool = False
    day_before: bool = False
    on_day: bool = True
    custom_days: Set[int] = field(default_factory=set)  # Store custom days before birthday
    
    def should_notify(self, days_until: int) -> bool:
        """Check if a notification should be sent based on days until birthday"""
        return (
            (self.week_before and days_until == 7) or
            (self.day_before and days_until == 1) or
            (self.on_day and days_until == 0) or
            (days_until in self.custom_days)
        )

@dataclass
class UserData:
    """Class for storing user data"""
    user_id: int
    username: str
    friends: Dict[str, Friend] = field(default_factory=dict)
    notification_pref: NotificationPreference = field(default_factory=NotificationPreference)
    state: str = "IDLE"  # Track conversation state
    temp_data: Dict = field(default_factory=dict)  # For storing temporary data during conversations

# In-memory database to store all user data
users: Dict[int, UserData] = {}

def get_user(user_id: int, username: str = None) -> UserData:
    """Get or create user data"""
    if user_id not in users:
        users[user_id] = UserData(user_id=user_id, username=username or f"user_{user_id}")
    return users[user_id]

def get_all_users() -> List[UserData]:
    """Get all users"""
    return list(users.values())

def get_upcoming_birthdays(days_ahead: int = 7) -> Dict[int, List[tuple]]:
    """
    Gets all birthdays coming up in the specified number of days
    Returns a dict mapping user_id to list of (friend, days_until) tuples
    """
    result = {}
    
    for user_id, user_data in users.items():
        user_birthdays = []
        
        for friend in user_data.friends.values():
            days_until = friend.days_until_birthday()
            
            if 0 <= days_until <= days_ahead:
                # Check if user wants to be notified on this day
                if user_data.notification_pref.should_notify(days_until):
                    user_birthdays.append((friend, days_until))
        
        if user_birthdays:
            result[user_id] = user_birthdays
            
    return result
