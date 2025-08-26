"""SQLAlchemy models defining User, Post, and RoleEnum for the application."""
import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
from database import Base

class RoleEnum(str, enum.Enum):
    """Enumeration for user roles in the system."""
    admin = "admin"
    user = "user"


class User(Base):
    """User model representing application users."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False)
    password_hash = Column(String(100), nullable=True)
    email = Column(String(100), unique=True, nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)

    posts = relationship("Post", back_populates="owner")


class Post(Base):
    """Post model representing blog posts created by users."""
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(50), nullable=False)
    content = Column(String(255), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="posts")
