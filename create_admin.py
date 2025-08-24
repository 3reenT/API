from database import SessionLocal
from models import User
from main import hash_password, generate_email

def create_admin():
    db = SessionLocal()
    try:
        username = "Admin"
        password = "admin123"
        email = generate_email(username)

        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"Admin '{username}")
            return

        admin = User(
            username=username,
            password_hash=hash_password(password),
            email=email,
            role="admin"
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"Admin created successfully: {admin.username} / {password} / {email}")
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
