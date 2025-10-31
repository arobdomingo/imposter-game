from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import os

engine = None
SessionLocal = None


def get_db():
    global engine, SessionLocal
    if not engine:
        if os.environ.get("TESTING") == "1":
            # Use in-memory SQLite for tests
            engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        else:
            host = os.environ.get("POSTGRES_HOST", "localhost")
            username = os.environ.get("POSTGRES_USER", "user")
            password = os.environ.get("POSTGRES_PASSWORD", "password")
            database = os.environ.get("POSTGRES_DB", username)

            DATABASE_URL = (
                f"postgresql+psycopg2://{username}:{password}@{host}:5432/{database}"
            )

            engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
