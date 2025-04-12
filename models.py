import logging
import json
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

class User(db.Model):
    """User model representing a Telegram user"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.BigInteger, unique=True, nullable=False)
    username = db.Column(db.String(255), nullable=True)
    state = db.Column(db.String(50), default=STATE_IDLE)
    temp_data = db.Column(db.Text, default="{}")
    
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


# Create app context wrapper functions

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
