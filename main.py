
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Annotated
import models
from database import engine, SessionLocal
from sqlalchemy.orm import Session

app = FastAPI()
models.Base.metadata.create_all(bind=engine)

class PostBase (BaseModel) :
    title: str
    content: str
    user_id: int


class UserBase(BaseModel) :
    username: str

from typing import Optional

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



@app.delete("/posts/{post_id}",status_code=status.HTTP_200_OK)
async def delete_post(post_id: int, db: db_dependency) :
    db_post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if db_post is None:
        raise HTTPException(status_code=404, detail='Post was not found' )
    db.delete(db_post)
    db.commit()


@app.post("/posts/", status_code=status.HTTP_201_CREATED)
async def create_post(post: PostBase, db: db_dependency):
    user = db.query(models.User).filter(models.User.id == post.user_id).first()
    if user is None:
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



@app.get("/posts/{post_id}", status_code=status.HTTP_200_OK)
async def read_post(post_id: int, db: db_dependency):
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail='Post was not found')
    return post


@app.post("/users/", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserBase, db: db_dependency):
    db_user = models.User(username=user.username)
    db.add(db_user)
    db.commit()


@app.get("/users/{user_id}", status_code=status.HTTP_200_OK)
async def read_user(user_id: int, db: db_dependency) :
    user = db.query(models.User). filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail='User not found')
    return user


@app.put("/users/{user_id}", status_code=status.HTTP_200_OK)
async def update_user(user_id: int, updated_user: UserBase, db: db_dependency):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.username = updated_user.username

    db.commit()
    db.refresh(db_user)
    return db_user

@app.put("/posts/{post_id}", status_code=status.HTTP_200_OK)
async def update_post(post_id: int, updated_post: PostUpdate, db: db_dependency):
    db_post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if db_post is None:
        raise HTTPException(status_code=404, detail="Post not found")

    if updated_post.title is not None:
        db_post.title = updated_post.title

    if updated_post.content is not None:
        db_post.content = updated_post.content

    if updated_post.user_id is not None:
        user = db.query(models.User).filter(models.User.id == updated_post.user_id).first()
        if user is None:
            raise HTTPException(status_code=400, detail="User ID does not exist")
        db_post.user_id = updated_post.user_id

    db.commit()
    db.refresh(db_post)
    return db_post


@app.get("/posts/", status_code=status.HTTP_200_OK)
async def get_all_posts(db: db_dependency):
    posts = db.query(models.Post).all()
    return posts

@app.get("/users/", status_code=status.HTTP_200_OK)
async def get_all_users(db: db_dependency):
    users = db.query(models.User).all()
    return users
