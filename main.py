from fastapi import FastAPI, HTTPException, Depends, status, Form, Response, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Annotated, Optional
from passlib.context import CryptContext
from enum import Enum
from jose import JWTError, jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import models
from database import engine, SessionLocal
from google.oauth2 import id_token
from google.auth.transport import requests as grequests

SECRET_KEY = "ba40b9361bec157bb888b1a6c382e9665063b0295742f146c110df81fafd6c3d"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

GOOGLE_CLIENT_ID = "651858540185-urprmiujjku7raaga77hcige4hbrivqh.apps.googleusercontent.com"


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def generate_email(username: str) -> str:
    parts = username.strip().split()
    if len(parts) < 2:
        raise ValueError("Username must contain first and last name")
    first_name = parts[0]
    last_name = parts[1]
    email = f"{first_name[0].upper()}{last_name}@gmail.com"
    return email

app = FastAPI()
models.Base.metadata.create_all(bind=engine)
app.mount("/static", StaticFiles(directory="frontend"), name="static")

class RoleEnum(str, Enum):
    admin = "admin"
    user = "user"

class UserBase(BaseModel):
    username: str
    password: str
    role: RoleEnum

class PostBase(BaseModel):
    title: str
    content: str
    user_id: int

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    user_id: Optional[int] = None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        email: str = payload.get("email")
        if username is None or email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(models.User).filter(
        models.User.username == username,
        models.User.email == email
    ).first()

    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())
    
@app.post("/login")
async def login(
    response: Response,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == email).first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token_data = {
        "sub": user.username,
        "email": user.email,
        "role": user.role.value,
        "id": user.id
    }
    token = create_access_token(token_data)

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,  
        samesite="Strict",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

    return {"message": f"Welcome {'Admin' if user.role.value=='admin' else 'User'} {user.username}"}


@app.post("/login/google")
async def login_google(response: Response, token: str = Form(...), db: Session = Depends(lambda: SessionLocal())):
    print("google_email")

    try:
        idinfo = id_token.verify_oauth2_token(token, grequests.Request(), GOOGLE_CLIENT_ID)
        google_email = idinfo.get("email")
        print(google_email)
        if not google_email:
            raise HTTPException(status_code=400, detail="Invalid Google token")

        user = db.query(models.User).filter(models.User.email == google_email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        jwt_token = create_access_token({"sub": user.username, "email": user.email, "id": user.id})
        response.set_cookie("access_token", jwt_token, httponly=True, secure=False, samesite="Strict")
        
        return {"message": f"Welcome {user.username} via Google"}
    except ValueError:
        raise HTTPException(status_code=400, detail="Google token verification failed")


@app.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully"}

@app.post("/users/", status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserBase, 
    db: db_dependency, 
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403, 
            detail=f"Access denied: Only admins can create new users"
        )

    try:
        generated_email = generate_email(user.username)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    hashed_password = hash_password(user.password)
    db_user = models.User(
        username=user.username, 
        password_hash=hashed_password,
        email=generated_email,   
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.get("/users/{user_id}", status_code=status.HTTP_200_OK)
async def read_user(
    user_id: int, 
    db: db_dependency, 
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403, 
            detail=f"Access denied: Only admins can view user details"
        )

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/user_posts/{username}")
async def get_user_posts(
    username: str, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if current_user.role != "admin" and current_user.username != username:
        raise HTTPException(
            status_code=403, 
            detail=f"Access denied: You can only view your own posts"
        )

    posts = db.query(models.Post).filter(models.Post.user_id == user.id).all()
    return posts


@app.get("/users/", status_code=status.HTTP_200_OK)
async def get_all_users(
    db: db_dependency,
    current_user: models.User = Depends(get_current_user)
):
    if current_user.role == "admin":
        return db.query(models.User).all()
    else:
        return db.query(models.User).filter(models.User.id == current_user.id).all()


@app.get("/posts/", status_code=status.HTTP_200_OK)
async def get_all_posts(
    current_user: models.User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    if current_user.role == "admin":
        return db.query(models.Post).all()
    else:
        return db.query(models.Post).filter(models.Post.user_id == current_user.id).all()


@app.get("/posts/{post_id}", status_code=status.HTTP_200_OK)
async def read_post(post_id: int, current_user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

@app.get("/me")
async def get_me(current_user: models.User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role.value 
    }

@app.post("/posts/", status_code=status.HTTP_201_CREATED)
async def create_post(
    post: PostBase, 
    db: db_dependency, 
    current_user: models.User = Depends(get_current_user)
):
    if current_user.id != post.user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=403, 
            detail="You can only create posts for yourself"
        )

    user = db.query(models.User).filter(models.User.id == post.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="User ID does not exist")

    db_post = models.Post(
        title=post.title, 
        content=post.content, 
        user_id=post.user_id
    )
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post


@app.put("/posts/{post_id}", status_code=status.HTTP_200_OK)
async def update_post(
    post_id: int, 
    updated_post: PostUpdate, 
    db: db_dependency, 
    current_user: models.User = Depends(get_current_user)
):
    db_post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if db_post.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed to update this post")

    if updated_post.title is not None:
        db_post.title = updated_post.title
    if updated_post.content is not None:
        db_post.content = updated_post.content
    if updated_post.user_id is not None:
        if current_user.role != "admin":  
            raise HTTPException(status_code=403, detail="Only admin can reassign post owner")
        user = db.query(models.User).filter(models.User.id == updated_post.user_id).first()
        if not user:
            raise HTTPException(status_code=400, detail="User ID does not exist")
        db_post.user_id = updated_post.user_id

    db.commit()
    db.refresh(db_post)
    return db_post
    
    
@app.delete("/posts/{post_id}", status_code=status.HTTP_200_OK)
async def delete_post(
    post_id: int, 
    db: db_dependency, 
    current_user: models.User = Depends(get_current_user)
):
    db_post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")

    if db_post.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed to delete this post")

    db.delete(db_post)
    db.commit()
    return {"detail": "Post deleted"}