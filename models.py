import logging
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from app import db
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# User state constants
STATE_IDLE = "IDLE"
STATE_ADDING_FRIEND_NAME = "ADDING_FRIEND_NAME"
STATE_ADDING_FRIEND_BIRTHDAY = "ADDING_FRIEND_BIRTHDAY"
STATE_SETTING_NOTIFICATION_TIME = "SETTING_NOTIFICATION_TIME"

class User(db.Model):
    """User model representing a Telegram user"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=False)
    username = db.Column(db.String(255), nullable=True)
    state = db.Column(db.String(50), default=STATE_IDLE)
    temp_data = db.Column(db.Text, default="{}")
    # Notification time in 24-hour format HH:MM, default 9:00 AM
    notification_time = db.Column(db.String(5), default="09:00")
    # Whether notifications are enabled
    notifications_enabled = db.Column(db.Boolean, default=True)
    
    # Relationships
    friends = relationship("Friend", back_populates="user", cascade="all, delete-orphan")

    def set_temp_data(self, data: Dict) -> None:
        """Store temporary data as JSON"""
        self.temp_data = json.dumps(data)
    
    def get_temp_data(self) -> Dict:
        """Get temporary data from JSON"""
        try:
            return json.loads(self.temp_data) if self.temp_data else {}
        except:
            return {}
            
    def get_notification_hour_minute(self) -> Tuple[int, int]:
        """Extract hour and minute from notification_time string"""
        try:
            hour, minute = self.notification_time.split(":")
            return int(hour), int(minute)
        except (ValueError, AttributeError):
            # Return default time (9:00 AM) if there's an error
            return 9, 0


class Friend(db.Model):
    """Friend model representing a birthday entry"""
    __tablename__ = 'friends'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    birth_date = db.Column(db.DateTime, nullable=False)
    
    # Relationship back to user
    user = relationship("User", back_populates="friends")
    
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


def get_user(telegram_id: int, username: str = None) -> User:
    """Get or create a user by telegram_id"""
    session = db.session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        
        if not user:
            user = User(telegram_id=telegram_id, username=username or f"user_{telegram_id}")
            session.add(user)
            session.commit()
            session.refresh(user)
        
        return user
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        session.rollback()
        raise
    finally:
        session.close()


def get_all_users() -> List[User]:
    """Get all users"""
    session = db.session()
    try:
        return session.query(User).all()
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        session.rollback()
        return []
    finally:
        session.close()


# Create app context wrapper function
def with_app_context(func):
    """Decorator to run a function within the app context."""
    def wrapper(*args, **kwargs):
        from app import app
        with app.app_context():
            return func(*args, **kwargs)
    return wrapper

def get_upcoming_birthdays(days_ahead: int = 0) -> Dict[int, List[Tuple[Friend, int]]]:
    """
    Gets all birthdays coming up in the specified number of days
    Returns a dict mapping telegram_id to list of (friend, days_until) tuples
    Only considers birthdays on the actual day (days_until == 0)
    """
    result = {}
    session = db.session()
    
    try:
        users = session.query(User).all()
        
        for user in users:
            user_birthdays = []
            
            for friend in user.friends:
                days_until = friend.days_until_birthday()
                
                if 0 <= days_until <= days_ahead:
                    # We only notify on the actual birthday
                    if days_until == 0:
                        user_birthdays.append((friend, days_until))
            
            if user_birthdays:
                result[user.telegram_id] = user_birthdays
                
        return result
    except Exception as e:
        logger.error(f"Error getting upcoming birthdays: {e}")
        return {}
    finally:
        session.close()


def save_friend(user_id: int, name: str, birth_date: datetime) -> Optional[Friend]:
    """Create or update a friend's birthday"""
    session = db.session()
    try:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            logger.error(f"User with telegram_id {user_id} not found")
            return None
        
        # Check if friend with this name already exists
        friend = session.query(Friend).filter(
            Friend.user_id == user.id,
            Friend.name == name
        ).first()
        
        if friend:
            # Update existing friend
            friend.birth_date = birth_date
        else:
            # Create new friend
            friend = Friend(user_id=user.id, name=name, birth_date=birth_date)
            session.add(friend)
        
        session.commit()
        session.refresh(friend)
        return friend
    except Exception as e:
        logger.error(f"Error saving friend: {e}")
        session.rollback()
        return None
    finally:
        session.close()


def delete_friend(user_id: int, friend_name: str) -> bool:
    """Delete a friend by name"""
    session = db.session()
    try:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            logger.error(f"User with telegram_id {user_id} not found")
            return False
        
        friend = session.query(Friend).filter(
            Friend.user_id == user.id,
            Friend.name == friend_name
        ).first()
        
        if friend:
            session.delete(friend)
            session.commit()
            return True
        
        return False
    except Exception as e:
        logger.error(f"Error deleting friend: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def get_user_friends(user_id: int) -> List[Friend]:
    """Get all friends for a user"""
    session = db.session()
    try:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            logger.error(f"User with telegram_id {user_id} not found")
            return []
        
        friends = session.query(Friend).filter(Friend.user_id == user.id).all()
        return friends
    except Exception as e:
        logger.error(f"Error getting user friends: {e}")
        return []
    finally:
        session.close()


def update_user_state(user_id: int, state: str, temp_data: Dict = None) -> None:
    """Update user state and temp data"""
    session = db.session()
    try:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            logger.error(f"User with telegram_id {user_id} not found")
            return
        
        user.state = state
        if temp_data is not None:
            user.set_temp_data(temp_data)
        
        session.commit()
    except Exception as e:
        logger.error(f"Error updating user state: {e}")
        session.rollback()
    finally:
        session.close()


def get_user_state(user_id: int) -> Tuple[str, Dict]:
    """Get user state and temp data"""
    session = db.session()
    try:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            logger.error(f"User with telegram_id {user_id} not found")
            return STATE_IDLE, {}
        
        return user.state, user.get_temp_data()
    except Exception as e:
        logger.error(f"Error getting user state: {e}")
        return STATE_IDLE, {}
    finally:
        session.close()


def update_notification_time(user_id: int, time_str: str) -> bool:
    """
    Update a user's notification time
    time_str should be in format "HH:MM" (24-hour format)
    """
    session = db.session()
    try:
        # Validate time format
        if not re.match(r"^([01]?[0-9]|2[0-3]):([0-5][0-9])$", time_str):
            logger.error(f"Invalid time format: {time_str}")
            return False
        
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            logger.error(f"User with telegram_id {user_id} not found")
            return False
        
        user.notification_time = time_str
        session.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating notification time: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def toggle_notifications(user_id: int, enabled: bool) -> bool:
    """Enable or disable notifications for a user"""
    session = db.session()
    try:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            logger.error(f"User with telegram_id {user_id} not found")
            return False
        
        user.notifications_enabled = enabled
        session.commit()
        return True
    except Exception as e:
        logger.error(f"Error toggling notifications: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def get_user_settings(user_id: int) -> Optional[Dict]:
    """Get a user's notification settings"""
    session = db.session()
    try:
        user = session.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            logger.error(f"User with telegram_id {user_id} not found")
            return None
        
        return {
            "notification_time": user.notification_time,
            "notifications_enabled": user.notifications_enabled
        }
    except Exception as e:
        logger.error(f"Error getting user settings: {e}")
        return None
    finally:
        session.close()


# Create context-wrapped versions of all database functions
# These should be at the end of the file, after all function definitions
get_user_with_context = with_app_context(get_user)
get_all_users_with_context = with_app_context(get_all_users)
get_upcoming_birthdays_with_context = with_app_context(get_upcoming_birthdays)
save_friend_with_context = with_app_context(save_friend)
delete_friend_with_context = with_app_context(delete_friend)
get_user_friends_with_context = with_app_context(get_user_friends)
update_user_state_with_context = with_app_context(update_user_state)
get_user_state_with_context = with_app_context(get_user_state)
update_notification_time_with_context = with_app_context(update_notification_time)
toggle_notifications_with_context = with_app_context(toggle_notifications)
get_user_settings_with_context = with_app_context(get_user_settings)
