"""Initialize the database by creating all tables defined in the models"""
from database import Base, engine
from models import *

print("Creating tables on the database...")

Base.metadata.create_all(bind=engine)

print("Tables created successfully!")
