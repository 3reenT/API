"""Main application module."""
import os
from datetime import datetime, timedelta
from enum import Enum
from typing import Annotated, Optional
# 2. Third-party imports
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, status, Form, Response, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests
import models
from database import engine, SessionLocal


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()
models.Base.metadata.create_all(bind=engine)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

class RoleEnum(str, Enum):
    """Enumeration for user roles in the system"""
    admin = "admin"
    user = "user"

class UserBase(BaseModel):
    """Base schema for User data"""
    username: str
    password: str
    role: RoleEnum

class PostBase(BaseModel):
    """Base schema for Post data"""
    title: str
    content: str
    user_id: int

class PostUpdate(BaseModel):
    """Schema for updating Post data"""
    title: Optional[str] = None
    content: Optional[str] = None
    user_id: Optional[int] = None


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Create a new JWT access token"""
    to_encode = data.copy()
    expire = datetime.now() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def set_jwt_cookie(response: Response, user: models.User):
    """ Generate a JWT for a user and store it in a secure HTTP-only cookie"""
    jwt_token = create_access_token({
        "sub": user.username,
        "email": user.email,
        "id": user.id,
        "role": user.role.value if hasattr(user.role, "value") else user.role
    })
    response.set_cookie(
        key="access_token",
        value=jwt_token,
        httponly=True,
        secure=True,
        samesite="Strict",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    return jwt_token


def hash_password(password: str):
    """Hash a plain text password using the configured password hashing context"""
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    """ Verify if a plain text password matches its hashed version"""
    return pwd_context.verify(plain_password, hashed_password)


def generate_email(username: str) -> str:
    """Generate an email address from a username (first and last name)"""
    parts = username.strip().split()
    if len(parts) < 2:
        raise ValueError("Username must contain first and last name")
    first_name, last_name = parts[0], parts[1]
    return f"{first_name[0].upper()}{last_name}@gmail.com"


def get_user_by_email(db: Session, email: str):
    """Retrieve a user from the database by their email address"""
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_id(db: Session, user_id: int):
    """Retrieve a user from the database by their ID"""
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_post_by_id(db: Session, post_id: int):
    """Retrieve a post from the database by its ID"""
    return db.query(models.Post).filter(models.Post.id == post_id).first()


def require_admin(user: models.User):
    """ Ensure the current user has admin privileges"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")


def check_ownership_or_admin(user: models.User, owner_id: int):
    """Verify if the current user is the owner of a resource or an admin"""
    if user.id != owner_id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed")

def create_new_user(db: Session,
                    username: str,
                    email: str,
                    password: Optional[str],
                    role: str = "user"):
    """Create and store a new user in the database"""
    hashed_password = hash_password(password) if password else None
    user = models.User(username=username,
                       email=email,
                       password_hash=hashed_password,
                       role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_db():
    """Dependency function that provides a database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

def get_current_user(request: Request, db: Session = Depends(get_db)):
    """Retrieve the currently authenticated user from the JWT token stored in cookies"""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(token,
                             SECRET_KEY,
                             algorithms=[ALGORITHM])
        username,email = payload.get("sub"), payload.get("email")
        if username is None or email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = db.query(models.User).filter(models.User.username == username,
                                        models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found") 
    return user


@app.get("/", response_class=HTMLResponse)
async def read_index():
    """Serve the main index HTML page of the frontend"""
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/login")
async def login(response: Response,
                email: str = Form(...),
                password: str = Form(...),
                db: Session = Depends(get_db)):
    """Authenticate a user using email and password"""
    user = get_user_by_email(db, email)
    if not user or not user.password_hash or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    set_jwt_cookie(response, user)
    return {
    "message": (
        f"Welcome {'Admin' if user.role.value == 'admin' else 'User'} "
        f"{user.username}"
    )
}

@app.post("/login/google")
async def login_google(response: Response,
                       token: str = Form(...),
                       db: Session = Depends(get_db)):
    """Authenticate a user via Google OAuth token"""
    print("Google token received:", token[:50], "...")

    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        print("Decoded token payload:", decoded)
        print("iat:", decoded.get("iat"), "exp:", decoded.get("exp"))
    except Exception as e:
        print("Failed to decode token:", e)

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10
        )
        print("Verified Google token:", idinfo)

        google_email = idinfo.get("email")
        google_name = idinfo.get("name", "GoogleUser")

        if not google_email:
            raise HTTPException(status_code=400, detail="Invalid Google token")

        user = get_user_by_email(db, google_email)
        if not user:
            user = create_new_user(
                db,
                username=google_name,
                email=google_email,
                password="ggg",
                role="user"
            )

        set_jwt_cookie(response, user)
        return {"message": f"Welcome {user.username} via Google"}

    except ValueError as e:
        print("Google token verification failed:", e)
        raise HTTPException(status_code=400, detail="Google token verification failed")


@app.post("/logout")
async def logout(response: Response):
    """Log out the current user by deleting the JWT access token cookie"""
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}


@app.post("/users/", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserBase,
                      db: db_dependency,
                      current_user: models.User = Depends(get_current_user)):
    """Create a new user. Only accessible by admin users"""
    require_admin(current_user)

    try:
        generated_email = generate_email(user.username)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    db_user = create_new_user(db,
                              username=user.username,
                              email=generated_email,
                              password=user.password,
                              role=user.role)
    return db_user


@app.get("/users/{user_id}", status_code=status.HTTP_200_OK)
async def read_user(user_id: int,
                    db: db_dependency,
                    current_user: models.User = Depends(get_current_user)):
    """Retrieve a user by ID. Only admin users can access this endpoint"""
    require_admin(current_user)
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.get("/users/", status_code=status.HTTP_200_OK)
async def get_all_users(db: db_dependency,
                        current_user: models.User = Depends(get_current_user)):
    """Retrieve all users. Admins see all users; regular users only see themselves"""
    if current_user.role == "admin":
        return db.query(models.User).all()
    return [current_user]


@app.get("/me")
async def get_me(current_user: models.User = Depends(get_current_user)):
    """Retrieve information about the currently authenticated user"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role.value
    }

@app.post("/posts/", status_code=status.HTTP_201_CREATED)
async def create_post(post: PostBase,
                      db: db_dependency,
                      current_user: models.User = Depends(get_current_user)):
    """Create a new post. Users can only create posts for themselves unless admin"""
    check_ownership_or_admin(current_user, post.user_id)

    if not get_user_by_id(db, post.user_id):
        raise HTTPException(status_code=400, detail="User ID does not exist")

    db_post = models.Post(title=post.title,
                          content=post.content,
                          user_id=post.user_id)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post


@app.get("/posts/", status_code=status.HTTP_200_OK)
async def get_all_posts(current_user: models.User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    """Retrieve all posts. Admins see all posts; regular users only see their own posts"""
    if current_user.role == "admin":
        return db.query(models.Post).all()
    return db.query(models.Post).filter(models.Post.user_id == current_user.id).all()


@app.get("/user_posts/{username}", status_code=status.HTTP_200_OK)
async def get_user_posts(
    username: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Retrieve posts by a specific username"""
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if current_user.role != "admin" and current_user.username != username:
        raise HTTPException(
            status_code=403,
            detail="Access denied: You can only view your own posts"
        )

    posts = db.query(models.Post).filter(models.Post.user_id == user.id).all()
    return posts

@app.get("/posts/{post_id}", status_code=status.HTTP_200_OK)
async def read_post(
    post_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve a single post by its ID"""
    post = get_post_by_id(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    check_ownership_or_admin(current_user, post.user_id)
    return post


@app.put("/posts/{post_id}", status_code=status.HTTP_200_OK)
async def update_post(post_id: int,
                      updated_post: PostUpdate,
                      db: db_dependency,
                      current_user: models.User = Depends(get_current_user)):
    """Update a post by ID. Users can only update their own posts; admin can update any post"""
    db_post = get_post_by_id(db, post_id)
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")

    check_ownership_or_admin(current_user, db_post.user_id)

    if updated_post.title is not None:
        db_post.title = updated_post.title
    if updated_post.content is not None:
        db_post.content = updated_post.content
    if updated_post.user_id is not None:
        require_admin(current_user)
        if not get_user_by_id(db, updated_post.user_id):
            raise HTTPException(status_code=400, detail="User ID does not exist")
        db_post.user_id = updated_post.user_id

    db.commit()
    db.refresh(db_post)
    return db_post


@app.delete("/posts/{post_id}", status_code=status.HTTP_200_OK)
async def delete_post(post_id: int,
                      db: db_dependency,
                      current_user: models.User = Depends(get_current_user)):
    """Delete a post by ID. Only the owner or admin can delete the post"""
    db_post = get_post_by_id(db, post_id)
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")

    check_ownership_or_admin(current_user, db_post.user_id)

    db.delete(db_post)
    db.commit()
    return {"detail": "Post deleted"}
