import asyncio
import logging
from fastapi import Depends, FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from nicegui import ui

from user_service.models.user import (
    UserRepository,
    get_user_repository,
    UserResponseSchema,
    Base as UserBase,
)
from user_service.models.friendship import Friendship, Base as FriendshipBase
from user_service.models.friendship_routes import router as friendships_router
import os

# ------------------ FASTAPI APP ------------------
app = FastAPI()
app.include_router(friendships_router)  # include friendship routes

# ------------------ Admin UI ------------------
ADMIN_PASSWORD = "admin123"
logger = logging.getLogger("uvicorn.error")

current_page = 1
current_page_size = 50
authenticated = False

# ------------------ DATABASE SETUP ------------------
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "postgres")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "db")

DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/{POSTGRES_DB}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables if they do not exist
UserBase.metadata.create_all(engine)
FriendshipBase.metadata.create_all(engine)

# ------------------ KEEP YOUR EXISTING NICEGUI UI CODE ------------------
# Copy everything from your original main.py (ui.page, user_list, show_admin_ui, etc.)
# Make sure all functionality for admin login & user CRUD remains unchanged.

__all__ = ["ui", "app"]
