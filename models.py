import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session, sessionmaker

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Setup SQLAlchemy
Base = declarative_base()
engine = create_engine(os.environ.get("DATABASE_URL"), echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class User(Base):
    """User model for database storage"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=True)
    state = Column(String, default="IDLE")
    friends = relationship("Friend", back_populates="user", cascade="all, delete-orphan")
    temp_data = Column(String, nullable=True)  # Stored as JSON
    
    def __repr__(self):
        return f"<User(user_id={self.user_id}, username={self.username})>"

class Friend(Base):
    """Friend model for database storage"""
    __tablename__ = "friends"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    birth_date = Column(DateTime, nullable=False)
    user = relationship("User", back_populates="friends")
    
    def days_until_birthday(self) -> int:
        """Calculate days until next birthday"""
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        next_birthday = self.next_birthday()
        
        # Calculate the difference in days
        delta = next_birthday - today
        return delta.days
    
    def next_birthday(self) -> datetime:
        """Get the date of the next birthday"""
        today = datetime.now()
        birth_date = self.birth_date
        
        # Set the birthday for this year
        this_year_birthday = datetime(today.year, birth_date.month, birth_date.day)
        
        # If the birthday has already passed this year, use next year's date
        if this_year_birthday < today:
            next_birthday = datetime(today.year + 1, self.birth_date.month, self.birth_date.day)
        else:
            next_birthday = this_year_birthday
            
        return next_birthday
    
    def __repr__(self):
        return f"<Friend(name={self.name}, birth_date={self.birth_date})>"

# Create all tables in the database
Base.metadata.create_all(bind=engine)

def get_user(user_id: int, username: str = None) -> User:
    """Get or create user data"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            user = User(user_id=user_id, username=username or f"user_{user_id}")
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    finally:
        db.close()

def get_all_users() -> List[User]:
    """Get all users"""
    db = SessionLocal()
    try:
        return db.query(User).all()
    finally:
        db.close()

def get_friend_by_name(user_id: int, friend_name: str) -> Optional[Friend]:
    """Get a friend by name for a specific user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return None
        
        friend = db.query(Friend).filter(
            Friend.user_id == user.id,
            Friend.name == friend_name
        ).first()
        
        return friend
    finally:
        db.close()

def add_friend(user_id: int, friend_name: str, birth_date: datetime) -> Friend:
    """Add a new friend for a user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            user = User(user_id=user_id)
            db.add(user)
            db.commit()
        
        friend = Friend(user_id=user.id, name=friend_name, birth_date=birth_date)
        db.add(friend)
        db.commit()
        db.refresh(friend)
        return friend
    finally:
        db.close()

def delete_friend(user_id: int, friend_name: str) -> bool:
    """Delete a friend for a user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return False
        
        friend = db.query(Friend).filter(
            Friend.user_id == user.id,
            Friend.name == friend_name
        ).first()
        
        if not friend:
            return False
        
        db.delete(friend)
        db.commit()
        return True
    finally:
        db.close()

def get_user_friends(user_id: int) -> List[Friend]:
    """Get all friends for a user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return []
        
        return db.query(Friend).filter(Friend.user_id == user.id).all()
    finally:
        db.close()

def update_user_state(user_id: int, state: str, temp_data: Optional[Dict] = None) -> bool:
    """Update user state and temporary data"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return False
        
        user.state = state
        if temp_data is not None:
            user.temp_data = json.dumps(temp_data)
        
        db.commit()
        return True
    finally:
        db.close()

def get_user_state(user_id: int) -> Tuple[str, Optional[Dict]]:
    """Get user state and temporary data"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return "IDLE", None
        
        temp_data = None
        if user.temp_data:
            try:
                temp_data = json.loads(user.temp_data)
            except:
                pass
        
        return user.state, temp_data
    finally:
        db.close()

def should_notify(days_until: int) -> bool:
    """Check if a notification should be sent based on days until birthday"""
    # Only send notifications on the actual birthday (days_until == 0)
    return days_until == 0

def get_upcoming_birthdays(days_ahead: int = 0) -> Dict[int, List[tuple]]:
    """
    Gets all birthdays coming up in the specified number of days
    Returns a dict mapping user_id to list of (friend, days_until) tuples
    """
    result = {}
    db = SessionLocal()
    
    try:
        users = db.query(User).all()
        
        for user in users:
            user_birthdays = []
            
            for friend in user.friends:
                days_until = friend.days_until_birthday()
                
                if 0 <= days_until <= days_ahead:
                    # Check if notification should be sent for this day
                    if should_notify(days_until):
                        user_birthdays.append((friend, days_until))
            
            if user_birthdays:
                result[user.user_id] = user_birthdays
        
        return result
    finally:
        db.close()