from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import os

engine = None
SessionLocal = None


def get_db():
    global engine, SessionLocal
    if not engine:
        host = os.environ.get("DATABASE_HOST", "localhost")
        username = os.environ.get("DATABASE_USER", "user")
        password = os.environ.get("DATABASE_PASSWORD", "password")

        DATABASE_URL = f"postgresql+psycopg2://{username}:{password}@{host}:5432/"

        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
