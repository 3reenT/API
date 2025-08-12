from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Annotated, Optional
import models
from database import engine, SessionLocal
from sqlalchemy.orm import Session
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from passlib.context import CryptContext
from pydantic import BaseModel
from enum import Enum
from passlib.context import CryptContext
from fastapi import Form

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str):
    return pwd_context.hash(password)

app = FastAPI()
models.Base.metadata.create_all(bind=engine)

class PostBase(BaseModel):
    title: str
    content: str
    user_id: int
    
class RoleEnum(str, Enum):
    admin = "admin"
    user = "user"

class UserBase(BaseModel):
    username: str
    password: str  
    role: RoleEnum

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
from fastapi.responses import HTMLResponse

@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.post("/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not pwd_context.verify(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if user.role == "admin":
        return {"message": f"Welcome Admin {user.username}"}
    else:
        return {"message": f"Welcome User {user.username}"}

@app.post("/users/", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserBase, db: Session = Depends(get_db)):
    hashed_password = hash_password(user.password)
    db_user = models.User(
        username=user.username,
        password_hash=hashed_password,
        role=user.role  
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/", status_code=status.HTTP_200_OK)
async def get_all_users(db: db_dependency):
    return db.query(models.User).all()

@app.get("/users/{user_id}", status_code=status.HTTP_200_OK)
async def read_user(user_id: int, db: db_dependency):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.put("/users/{user_id}", status_code=status.HTTP_200_OK)
async def update_user(user_id: int, updated_user: UserBase, db: db_dependency):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    db_user.username = updated_user.username
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/posts/", status_code=status.HTTP_201_CREATED)
async def create_post(post: PostBase, db: db_dependency):
    user = db.query(models.User).filter(models.User.id == post.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="User ID does not exist")
    db_post = models.Post(title=post.title, content=post.content, user_id=post.user_id)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    return db_post

@app.get("/posts/", status_code=status.HTTP_200_OK)
async def get_all_posts(db: db_dependency):
    return db.query(models.Post).all()

@app.get("/posts/{post_id}", status_code=status.HTTP_200_OK)
async def read_post(post_id: int, db: db_dependency):
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

@app.put("/posts/{post_id}", status_code=status.HTTP_200_OK)
async def update_post(post_id: int, updated_post: PostUpdate, db: db_dependency):
    db_post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")
    if updated_post.title is not None:
        db_post.title = updated_post.title
    if updated_post.content is not None:
        db_post.content = updated_post.content
    if updated_post.user_id is not None:
        user = db.query(models.User).filter(models.User.id == updated_post.user_id).first()
        if not user:
            raise HTTPException(status_code=400, detail="User ID does not exist")
        db_post.user_id = updated_post.user_id
    db.commit()
    db.refresh(db_post)
    return db_post

@app.delete("/posts/{post_id}", status_code=status.HTTP_200_OK)
async def delete_post(post_id: int, db: db_dependency):
    db_post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")
    db.delete(db_post)
    db.commit()
    return {"detail": "Post deleted"}