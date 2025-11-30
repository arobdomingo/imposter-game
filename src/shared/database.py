from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import os

engine = None
SessionLocal = None


def get_db():
    global engine, SessionLocal
    if not engine:
        # Check if DATABASE_URL is provided (common in Render, Heroku, etc.)
        database_url = os.environ.get("DATABASE_URL")
        
        if database_url:
            # If DATABASE_URL is provided, use it directly
            # Convert postgresql:// to postgresql+psycopg2:// if needed
            if database_url.startswith("postgresql://"):
                database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
            DATABASE_URL = database_url
        else:
            # Fall back to individual environment variables
            host = os.environ.get("POSTGRES_HOST", "localhost")
            username = os.environ.get("POSTGRES_USER", "user")
            password = os.environ.get("POSTGRES_PASSWORD", "password")
            database = os.environ.get("POSTGRES_DB", username)
            
            # Don't use "db" as default - that's only for Docker Compose
            if host == "db" and not os.environ.get("POSTGRES_HOST"):
                host = "localhost"

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
