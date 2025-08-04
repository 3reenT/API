from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

URL_DATABASE = "mysql+pymysql://root:areen.rr18@localhost:3306/blogapplication"
print("Connecting to:", URL_DATABASE)


engine = create_engine(URL_DATABASE, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
