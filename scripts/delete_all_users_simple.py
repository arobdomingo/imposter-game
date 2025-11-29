#!/usr/bin/env python3
"""
Simple script to delete ALL users and related data.
No confirmation prompts - use with caution!
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

load_dotenv()

host = os.environ.get("POSTGRES_HOST", "localhost")
if host == "db":
    host = "localhost"

os.environ["DATABASE_HOST"] = host
os.environ["DATABASE_USER"] = os.environ.get("POSTGRES_USER", "postgres")
os.environ["DATABASE_PASSWORD"] = os.environ.get("POSTGRES_PASSWORD", "password")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.shared.database import get_db  # noqa: E402


async def delete_all():
    """Delete all users and related data"""
    db = next(get_db())

    try:
        from sqlalchemy import text

        print("Deleting all data...")

        # Delete in order (respecting foreign keys)
        tables = [
            "votes",
            "clues",
            "chat_messages",
            "players",
            "games",
            "lobby_members",
            "lobbies",
            "friendships",
            "events",  # May not exist, but try anyway
            "users",
        ]

        for table in tables:
            try:
                result = db.execute(text(f"DELETE FROM {table}"))
                count = result.rowcount
                print(f"  ✓ Deleted {count} rows from {table}")
            except Exception as e:
                print(f"  ⚠ Could not delete from {table}: {e}")

        db.commit()
        print("\n[SUCCESS] All data deleted!")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback

        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(delete_all())

