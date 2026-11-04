"""
User model for authentication
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from ..database import Base


class User(Base):
    """User model for authentication"""
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    role = Column(String(20), default="lawyer")  # admin, lawyer, staff
    is_active = Column(Boolean, default=True)
    lawyer_id = Column(Integer, ForeignKey("lawyer.lawyer_id", ondelete="SET NULL", onupdate="CASCADE"), unique=True)
    must_change_password = Column(Boolean, nullable=False, default=False)
    last_login_at = Column(DateTime)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    lawyer = relationship("Lawyer")
