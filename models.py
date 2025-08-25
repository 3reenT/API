from sqlalchemy import Boolean, Column, Integer, String
from database import Base
from sqlalchemy.orm import relationship
from database import Base
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import enum
from sqlalchemy import Enum

print("Base from database =", Base)

class RoleEnum(str, enum.Enum):
    admin = "admin"
    user = "user"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False)
    password_hash = Column(String(100), nullable=False) 
    email = Column(String(100), unique=True, nullable=False)  
    role = Column(Enum(RoleEnum), nullable=False)  
    posts = relationship("Post", back_populates="owner")

class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(50))
    content = Column(String(50))
    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="posts")