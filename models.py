import logging
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session
from sqlalchemy.dialects.postgresql import ARRAY

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set up SQLAlchemy with PostgreSQL
DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

# SQLAlchemy models
class User(Base):
    """Database model for a user"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100), nullable=True)
    state = Column(String(50), default="IDLE")
    temp_data = Column(Text, default="{}")  # JSON string
    
    # Relationships
    friends = relationship("Friend", back_populates="user", cascade="all, delete-orphan")
    notification_pref = relationship("NotificationPreference", uselist=False, back_populates="user", 
                                    cascade="all, delete-orphan")

class Friend(Base):
    """Database model for a friend"""
    __tablename__ = "friends"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    birth_date = Column(Date, nullable=False)
    
    # Relationship
    user = relationship("User", back_populates="friends")
    
    def days_until_birthday(self) -> int:
        """Calculate days until next birthday"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        next_bd_month = self.birth_date.month
        next_bd_day = self.birth_date.day
        next_bd_year = today.year
        
        next_birthday = datetime(next_bd_year, next_bd_month, next_bd_day)
        
        # If birthday has already occurred this year, calculate for next year
        if next_birthday < today:
            next_birthday = datetime(next_bd_year + 1, next_bd_month, next_bd_day)
        
        return (next_birthday - today).days
    
    def next_birthday(self) -> datetime:
        """Get the date of the next birthday"""
        today = datetime.now()
        next_bd_month = self.birth_date.month
        next_bd_day = self.birth_date.day
        next_bd_year = today.year
        
        next_birthday = datetime(next_bd_year, next_bd_month, next_bd_day)
        
        # If birthday has already occurred this year, calculate for next year
        if next_birthday < today:
            next_birthday = datetime(next_bd_year + 1, next_bd_month, next_bd_day)
            
        return next_birthday

class NotificationPreference(Base):
    """Database model for notification preferences"""
    __tablename__ = "notification_preferences"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    week_before = Column(Boolean, default=False)
    day_before = Column(Boolean, default=False)
    on_day = Column(Boolean, default=True)
    custom_days = Column(Text, default="[]")  # JSON array of integers
    
    # Relationship
    user = relationship("User", back_populates="notification_pref")
    
    def get_custom_days(self) -> Set[int]:
        """Get custom days as a set"""
        try:
            return set(json.loads(self.custom_days))
        except:
            return set()
    
    def set_custom_days(self, days: Set[int]) -> None:
        """Set custom days from a set"""
        self.custom_days = json.dumps(list(days))
    
    def should_notify(self, days_until: int) -> bool:
        """Check if a notification should be sent based on days until birthday"""
        return (
            (self.week_before and days_until == 7) or
            (self.day_before and days_until == 1) or
            (self.on_day and days_until == 0) or
            (days_until in self.get_custom_days())
        )

# Helper class for storing temporary user state
class UserData:
    """Class for storing user data during interactions"""
    def __init__(self, db_user: User):
        self.db_user = db_user
        self.user_id = db_user.user_id
        self.username = db_user.username
        self.state = db_user.state
        
        # Parse temp data from JSON
        try:
            self.temp_data = json.loads(db_user.temp_data)
        except:
            self.temp_data = {}
    
    def save(self, session: Session) -> None:
        """Save changes back to the database"""
        self.db_user.state = self.state
        self.db_user.temp_data = json.dumps(self.temp_data)
        session.commit()

def get_db_session() -> Session:
    """Get database session"""
    return SessionLocal()

def get_or_create_user(session: Session, user_id: int, username: str = None) -> User:
    """Get or create a user in the database"""
    user = session.query(User).filter(User.user_id == user_id).first()
    
    if not user:
        # Create new user
        user = User(user_id=user_id, username=username or f"user_{user_id}")
        session.add(user)
        
        # Create notification preferences
        notification_pref = NotificationPreference(user=user)
        session.add(notification_pref)
        
        session.commit()
    
    return user

def get_user(user_id: int, username: str = None) -> UserData:
    """Get or create user data wrapper"""
    session = get_db_session()
    try:
        db_user = get_or_create_user(session, user_id, username)
        return UserData(db_user)
    finally:
        session.close()

def get_all_users() -> List[Tuple[int, str]]:
    """Get all users' IDs and usernames"""
    session = get_db_session()
    try:
        users = session.query(User.user_id, User.username).all()
        return users
    finally:
        session.close()

def get_user_friends(user_id: int) -> Dict[str, Friend]:
    """Get all friends for a user"""
    session = get_db_session()
    try:
        db_user = get_or_create_user(session, user_id)
        return {friend.name: friend for friend in db_user.friends}
    finally:
        session.close()

def add_friend(user_id: int, friend_name: str, birth_date: datetime) -> Friend:
    """Add a friend to a user's list"""
    session = get_db_session()
    try:
        db_user = get_or_create_user(session, user_id)
        
        # Check if friend already exists, update if so
        existing_friend = None
        for friend in db_user.friends:
            if friend.name == friend_name:
                existing_friend = friend
                break
        
        if existing_friend:
            existing_friend.birth_date = birth_date
            friend = existing_friend
        else:
            friend = Friend(user=db_user, name=friend_name, birth_date=birth_date)
            session.add(friend)
        
        session.commit()
        return friend
    finally:
        session.close()

def remove_friend(user_id: int, friend_name: str) -> bool:
    """Remove a friend from a user's list"""
    session = get_db_session()
    try:
        db_user = get_or_create_user(session, user_id)
        
        for friend in db_user.friends:
            if friend.name == friend_name:
                session.delete(friend)
                session.commit()
                return True
        
        return False
    finally:
        session.close()

def get_notification_preferences(user_id: int) -> NotificationPreference:
    """Get notification preferences for a user"""
    session = get_db_session()
    try:
        db_user = get_or_create_user(session, user_id)
        return db_user.notification_pref
    finally:
        session.close()

def update_notification_preferences(user_id: int, week_before: bool = None, 
                                  day_before: bool = None, on_day: bool = None) -> NotificationPreference:
    """Update notification preferences for a user"""
    session = get_db_session()
    try:
        db_user = get_or_create_user(session, user_id)
        prefs = db_user.notification_pref
        
        if week_before is not None:
            prefs.week_before = week_before
        if day_before is not None:
            prefs.day_before = day_before
        if on_day is not None:
            prefs.on_day = on_day
        
        session.commit()
        return prefs
    finally:
        session.close()

def add_custom_notification_day(user_id: int, days: int) -> Set[int]:
    """Add a custom notification day"""
    session = get_db_session()
    try:
        db_user = get_or_create_user(session, user_id)
        prefs = db_user.notification_pref
        
        custom_days = prefs.get_custom_days()
        custom_days.add(days)
        prefs.set_custom_days(custom_days)
        
        session.commit()
        return custom_days
    finally:
        session.close()

def remove_custom_notification_day(user_id: int, days: int) -> Set[int]:
    """Remove a custom notification day"""
    session = get_db_session()
    try:
        db_user = get_or_create_user(session, user_id)
        prefs = db_user.notification_pref
        
        custom_days = prefs.get_custom_days()
        if days in custom_days:
            custom_days.remove(days)
        prefs.set_custom_days(custom_days)
        
        session.commit()
        return custom_days
    finally:
        session.close()

def get_upcoming_birthdays(days_ahead: int = 7) -> Dict[int, List[Tuple[Friend, int]]]:
    """
    Gets all birthdays coming up in the specified number of days
    Returns a dict mapping user_id to list of (friend, days_until) tuples
    """
    result = {}
    session = get_db_session()
    
    try:
        users = session.query(User).all()
        
        for user in users:
            user_birthdays = []
            
            for friend in user.friends:
                days_until = friend.days_until_birthday()
                
                if 0 <= days_until <= days_ahead:
                    # Check if user wants to be notified on this day
                    if user.notification_pref.should_notify(days_until):
                        user_birthdays.append((friend, days_until))
            
            if user_birthdays:
                result[user.user_id] = user_birthdays
        
        return result
    finally:
        session.close()

# Create tables
Base.metadata.create_all(engine)
