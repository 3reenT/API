
from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Annotated
import models
from database import engine, SessionLocal
from sqlalchemy.orm import Session
from fastapi import Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

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

app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# root -> index.html
@app.get("/", response_class=FileResponse)
async def read_root():
    return FileResponse("frontend/index.html")




from fastapi.responses import HTMLResponse

@app.get("/users/html", response_class=HTMLResponse)
async def users_html(db: db_dependency):
    users = db.query(models.User).all()
    html = """
    <html>
    <head>
        <link rel="stylesheet" href="/frontend/style.css">
        <title>All Users</title>
    </head>
    <body>
    <div class="container">
    <header class="header">
        <h1>All Users</h1>
    </header>
    <div class="card">
    <table border="1" style="width:100%; border-collapse: collapse; text-align:left;">
        <tr>
            <th>ID</th>
            <th>Username</th>
        </tr>
    """
    for u in users:
        html += f"<tr><td>{u.id}</td><td>{u.username}</td></tr>"
    html += """
    </table>
    <div style="margin-top:12px;">
        <a class="btn" href="/frontend/index.html">Back</a>
    </div>
    </div></div></body></html>
    """
    return html


@app.get("/posts/html", response_class=HTMLResponse)
async def posts_html(db: db_dependency):
    posts = db.query(models.Post).all()
    html = """
    <html>
    <head>
        <link rel="stylesheet" href="/frontend/style.css">
        <title>All Posts</title>
    </head>
    <body>
    <div class="container">
    <header class="header">
        <h1>All Posts</h1>
    </header>
    <div class="card">
    <table border="1" style="width:100%; border-collapse: collapse; text-align:left;">
        <tr>
            <th>ID</th>
            <th>Title</th>
            <th>Content</th>
            <th>User ID</th>
        </tr>
    """
    for p in posts:
        html += f"<tr><td>{p.id}</td><td>{p.title}</td><td>{p.content}</td><td>{p.user_id}</td></tr>"
    html += """
    </table>
    <div style="margin-top:12px;">
        <a class="btn" href="/frontend/index.html">Back</a>
    </div>
    </div></div></body></html>
    """
    return html

@app.delete("/posts/{post_id}",status_code=status.HTTP_200_OK)
async def delete_post(post_id: int, db: db_dependency) :
    db_post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if db_post is None:
        raise HTTPException(status_code=404, detail='Post was not found' )
    db.delete(db_post)
    db.commit()


@app.post("/posts/", status_code=status.HTTP_201_CREATED)
async def create_post(
    title: str = Form(...),
    content: str = Form(...),
    user_id: int = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        # if user id invalid, show a simple HTML error page (not JSON)
        html = f"""
        <html><head><link rel="stylesheet" href="/frontend/style.css"><title>Error</title></head>
        <body>
          <div class="container">
            <div class="card">
              <h2>Invalid User ID</h2>
              <p>User with ID <strong>{user_id}</strong> does not exist.</p>
              <div style="margin-top:12px;">
                <a class="btn" href="/frontend/create_post.html">Back to Create Post</a>
              </div>
            </div>
          </div>
        </body></html>
        """
        return HTMLResponse(content=html, status_code=400)

    db_post = models.Post(title=title, content=content, user_id=user_id)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    # redirect to posts_html so browser shows the table
    return RedirectResponse(url="/posts/html", status_code=status.HTTP_303_SEE_OTHER)



@app.get("/posts/{post_id}", status_code=status.HTTP_200_OK)
async def read_post(post_id: int, db: db_dependency):
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if post is None:
        raise HTTPException(status_code=404, detail='Post was not found')
    return post


@app.post("/users/", status_code=status.HTTP_201_CREATED)
async def create_user(
    username: str = Form(...),
    db: Session = Depends(get_db)
):
    db_user = models.User(username=username)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return RedirectResponse(url="/users/html", status_code=status.HTTP_303_SEE_OTHER)


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


@app.post("/users/", status_code=status.HTTP_201_CREATED)
async def create_user(
    username: str = Form(...),
    db: Session = Depends(get_db)
):
    db_user = models.User(username=username)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    # redirect to users_html so browser shows the table, use 303 See Other
    return RedirectResponse(url="/users/html", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/posts/", status_code=status.HTTP_201_CREATED)
async def create_post(
    title: str = Form(...),
    content: str = Form(...),
    user_id: int = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        # if user id invalid, show a simple HTML error page (not JSON)
        html = f"""
        <html><head><link rel="stylesheet" href="/frontend/style.css"><title>Error</title></head>
        <body>
          <div class="container">
            <div class="card">
              <h2>Invalid User ID</h2>
              <p>User with ID <strong>{user_id}</strong> does not exist.</p>
              <div style="margin-top:12px;">
                <a class="btn" href="/frontend/create_post.html">Back to Create Post</a>
              </div>
            </div>
          </div>
        </body></html>
        """
        return HTMLResponse(content=html, status_code=400)

    db_post = models.Post(title=title, content=content, user_id=user_id)
    db.add(db_post)
    db.commit()
    db.refresh(db_post)
    # redirect to posts_html so browser shows the table
    return RedirectResponse(url="/posts/html", status_code=status.HTTP_303_SEE_OTHER)

