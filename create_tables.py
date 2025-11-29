from sqlalchemy import create_engine
from user_service.models.user import Base as UserBase
from user_service.models.friendship import Base as FriendshipBase
import os

# --- Load environment variables from docker-compose ---
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "db")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "postgres")

# --- Build database URL ---
DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}/{POSTGRES_DB}"
)

# --- Connect to DB ---
engine = create_engine(DATABASE_URL)

# --- Create tables ---
print("🔄 Creating 'users' and 'friendships' tables...")
UserBase.metadata.create_all(engine)
FriendshipBase.metadata.create_all(engine)
print("✅ Tables created successfully!")
