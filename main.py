from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Annotated, Optional
import models
from database import engine, SessionLocal
from sqlalchemy.orm import Session
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from utils import hash_password
from fastapi import Form
from passlib.context import CryptContext
from fastapi.security import HTTPBasic

app = FastAPI()
models.Base.metadata.create_all(bind=engine)

security = HTTPBasic()


class PostBase(BaseModel):
    title: str
    content: str
    user_id: int

class UserBase(BaseModel):
    username: str
    password: str  # كلمة السر نص عادي

class AdminBase(BaseModel):
    username: str
    password: str

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


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    admin = db.query(models.Admin).filter(models.Admin.username == username).first()
    if admin:
        if pwd_context.verify(password, admin.password_hash):
            return {"message": f"Welcome Admin {username}!", "role": "admin"}
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password for admin")

    user = db.query(models.User).filter(models.User.username == username).first()
    if user:
        if pwd_context.verify(password, user.password_hash):
            return {"message": f"Welcome User {username}!", "role": "user"}
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password for user")

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")


@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("frontend/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

app.mount("/static", StaticFiles(directory="frontend"), name="static")



@app.post("/admins/", status_code=status.HTTP_201_CREATED)
async def create_admin(admin: AdminBase, db: db_dependency):
    hashed_password = hash_password(admin.password)
    db_admin = models.Admin(username=admin.username, password_hash=hashed_password)
    db.add(db_admin)
    db.commit()
    db.refresh(db_admin)
    return db_admin

@app.get("/admins/", status_code=status.HTTP_200_OK)
def get_all_admins(db: Session = Depends(get_db)):
    return db.query(models.Admin).all()
from utils import hash_password  # لازم تكون عامل import

@app.post("/users/", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserBase, db: db_dependency):
    hashed_pwd = hash_password(user.password)  # تشفير الباسوورد
    db_user = models.User(username=user.username, password_hash=hashed_pwd)  # خزّن الهاش
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.get("/users/", status_code=status.HTTP_200_OK)
def get_all_users(db: Session = Depends(get_db)):
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
    db_user.password = updated_user.password
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



@app.get("/posts1/", status_code=status.HTTP_200_OK)
def get_all_posts(db: Session = Depends(get_db)):
    posts = db.query(models.Post).all()
    return posts

@app.get("/posts/", status_code=status.HTTP_200_OK)
async def get_posts(credentials: HTTPBasicCredentials = Depends(security), db: Session = Depends(get_db)):
    admin = db.query(models.Admin).filter(models.Admin.username == credentials.username).first()
    if admin and verify_password(credentials.password, admin.password_hash):
        return db.query(models.Post).all()

    user = db.query(models.User).filter(models.User.username == credentials.username).first()
    if user and user.password_hash and verify_password(credentials.password, user.password_hash):
        return db.query(models.Post).filter(models.Post.user_id == user.id).all()

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

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
