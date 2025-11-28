#!/usr/bin/env python3
"""
Clean orphaned data - remove lobbies/games that reference non-existent users
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


async def clean_orphaned_data():
    """Remove data that references non-existent users"""
    db = next(get_db())

    try:
        from sqlalchemy import text, select
        from src.user_service.models.user import User

        # Get all existing user IDs
        users = db.execute(select(User.id)).scalars().all()
        user_ids = set(users)

        print(f"Found {len(user_ids)} existing users")

        if len(user_ids) == 0:
            print("No users found. Deleting all related data...")
            # Delete everything
            tables = [
                "votes",
                "clues",
                "chat_messages",
                "players",
                "games",
                "lobby_members",
                "lobbies",
                "friendships",
            ]
            for table in tables:
                try:
                    db.execute(text(f"DELETE FROM {table}"))
                    print(f"  ✓ Cleaned {table}")
                except Exception:
                    pass
            db.commit()
            return

        # Find orphaned lobby members
        result = db.execute(
            text("""
            SELECT DISTINCT user_id FROM lobby_members 
            WHERE user_id NOT IN (SELECT id FROM users)
        """)
        )
        orphaned_user_ids = [row[0] for row in result]

        if orphaned_user_ids:
            print(f"Found {len(orphaned_user_ids)} orphaned lobby members")
            # Delete orphaned lobby members and their lobbies
            db.execute(
                text("""
                DELETE FROM lobby_members 
                WHERE user_id NOT IN (SELECT id FROM users)
            """)
            )
            print("  ✓ Cleaned orphaned lobby members")

        # Find and delete lobbies with no members
        db.execute(
            text("""
            DELETE FROM lobbies 
            WHERE id NOT IN (SELECT DISTINCT lobby_id FROM lobby_members)
        """)
        )
        print("  ✓ Cleaned empty lobbies")

        # Find orphaned players
        db.execute(
            text("""
            DELETE FROM players 
            WHERE user_id NOT IN (SELECT id FROM users)
        """)
        )
        print("  ✓ Cleaned orphaned players")

        # Find and delete games with no players
        db.execute(
            text("""
            DELETE FROM games 
            WHERE id NOT IN (SELECT DISTINCT game_id FROM players)
        """)
        )
        print("  ✓ Cleaned empty games")

        # Clean other orphaned data
        db.execute(
            text("""
            DELETE FROM votes 
            WHERE voter_id NOT IN (SELECT id FROM players)
            OR target_id NOT IN (SELECT id FROM players)
        """)
        )
        print("  ✓ Cleaned orphaned votes")

        db.execute(
            text("""
            DELETE FROM clues 
            WHERE player_id NOT IN (SELECT id FROM players)
        """)
        )
        print("  ✓ Cleaned orphaned clues")

        db.execute(
            text("""
            DELETE FROM chat_messages 
            WHERE user_id NOT IN (SELECT id FROM users)
        """)
        )
        print("  ✓ Cleaned orphaned chat messages")

        db.commit()
        print("\n[SUCCESS] Orphaned data cleaned!")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback

        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(clean_orphaned_data())
