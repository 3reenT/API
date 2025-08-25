import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

load_dotenv()

URL_DATABASE = os.getenv("DATABASE_URL")

if not URL_DATABASE:
    raise ValueError("DATABASE_URL environment variable not set!")

print("Connecting to:", URL_DATABASE)

engine = create_engine(URL_DATABASE, echo=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
