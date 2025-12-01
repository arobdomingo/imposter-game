from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import logging

import os

logger = logging.getLogger(__name__)

engine = None
SessionLocal = None


def get_db():
    global engine, SessionLocal
    if not engine:
        # Check if DATABASE_URL is provided (common in Render, Heroku, etc.)
        # This should ALWAYS be used if available, as it's the standard way
        database_url = os.environ.get("DATABASE_URL")

        if database_url and database_url.strip():
            # If DATABASE_URL is provided, use it directly
            # Convert postgresql:// to postgresql+psycopg2:// if needed
            if database_url.startswith("postgresql://"):
                database_url = database_url.replace(
                    "postgresql://", "postgresql+psycopg2://", 1
                )
            DATABASE_URL = database_url.strip()
            logger.info("Using DATABASE_URL from environment")
        else:
            # Fall back to individual environment variables (only if DATABASE_URL is not set)
            host = os.environ.get("POSTGRES_HOST", "localhost")
            username = os.environ.get("POSTGRES_USER", "user")
            password = os.environ.get("POSTGRES_PASSWORD", "password")
            database = os.environ.get("POSTGRES_DB", username)

            # Never use "db" as host unless explicitly set (it's only for Docker Compose)
            # If somehow we get "db" as default, use localhost instead
            if host == "db":
                if "POSTGRES_HOST" in os.environ:
                    # POSTGRES_HOST was explicitly set to "db" (Docker Compose)
                    logger.info("Using POSTGRES_HOST='db' (Docker Compose environment)")
                else:
                    # POSTGRES_HOST was not set, but we got "db" somehow - use localhost
                    host = "localhost"
                    logger.warning(
                        "POSTGRES_HOST defaulted to 'db', but not explicitly set. Using 'localhost' instead."
                    )

            DATABASE_URL = (
                f"postgresql+psycopg2://{username}:{password}@{host}:5432/{database}"
            )
            logger.info(f"Using individual POSTGRES_* variables (host: {host})")

        # Log connection string (without password for security)
        safe_url = DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else "***"
        logger.info(f"Database connection: postgresql+psycopg2://***@{safe_url}")

        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
