#!/usr/bin/env python3
"""
Script to delete ALL users from the database.
WARNING: This will delete all users and may affect related data.
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Set environment variable mapping
host = os.environ.get("POSTGRES_HOST", "localhost")
if host == "db":
    host = "localhost"

os.environ["DATABASE_HOST"] = host
os.environ["DATABASE_USER"] = os.environ.get("POSTGRES_USER", "postgres")
os.environ["DATABASE_PASSWORD"] = os.environ.get("POSTGRES_PASSWORD", "password")

print(f"Connecting to database: {host}:5432, user: {os.environ['DATABASE_USER']}")

# Add project root directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.shared.database import get_db  # noqa: E402


async def delete_all_users(confirm=False):
    """Delete ALL users from the database"""
    print("=" * 60)
    print("WARNING: This will delete ALL users from the database!")
    print("This includes:")
    print("  - All user accounts")
    print("  - All related data (lobbies, games, players, etc.)")
    print("  - All friendships")
    print("=" * 60)

    # Check for command line argument
    import sys

    if not confirm and "--confirm" not in sys.argv:
        print("\nTo delete all users, run with --confirm flag:")
        print("  python scripts/delete_all_users.py --confirm")
        print("\nOr use the interactive version (may not work in Docker):")
        print("  python scripts/delete_all_users.py")
        return

    # Get confirmation if not already confirmed
    if not confirm:
        try:
            response = input(
                "\nAre you absolutely sure you want to delete ALL users? (type 'DELETE ALL' to confirm): "
            )
            if response != "DELETE ALL":
                print("Cancelled. No users were deleted.")
                return
        except EOFError:
            # Running in non-interactive mode, require --confirm flag
            print(
                "\n[ERROR] Cannot read input. Use --confirm flag for non-interactive mode."
            )
            return

    # Get database session
    db = next(get_db())

    try:
        from src.user_service.models.user import User
        from sqlalchemy import select, delete, text

        # Count users first
        stmt = select(User)
        all_users = db.execute(stmt).scalars().all()
        total_count = len(all_users)

        if total_count == 0:
            print("[INFO] No users found in database.")
            return

        print(f"\n[INFO] Found {total_count} users to delete")

        # Show first 10 users as preview
        print("\n[PREVIEW] First 10 users:")
        for i, user in enumerate(all_users[:10]):
            print(f"  {i + 1}. {user.name} ({user.email}) - ID: {user.id}")
        if total_count > 10:
            print(f"  ... and {total_count - 10} more users")

        # Final confirmation (skip if --confirm flag is used)
        if "--confirm" not in sys.argv:
            try:
                print("\n" + "=" * 60)
                response2 = input(
                    "This is your LAST chance. Type 'YES DELETE' to proceed: "
                )
                if response2 != "YES DELETE":
                    print("Cancelled. No users were deleted.")
                    return
            except EOFError:
                print(
                    "\n[ERROR] Cannot read input. Use --confirm flag for non-interactive mode."
                )
                return

        # Delete related data first (due to foreign key constraints)
        print("\n[STEP 1] Deleting related game data...")

        # Delete in order to respect foreign key constraints
        # Votes -> Clues -> Players -> Games -> LobbyMembers -> Lobbies
        try:
            # Delete votes
            db.execute(text("DELETE FROM votes"))
            print("  ✓ Deleted votes")

            # Delete clues
            db.execute(text("DELETE FROM clues"))
            print("  ✓ Deleted clues")

            # Delete chat messages
            db.execute(text("DELETE FROM chat_messages"))
            print("  ✓ Deleted chat messages")

            # Delete players
            db.execute(text("DELETE FROM players"))
            print("  ✓ Deleted players")

            # Delete games
            db.execute(text("DELETE FROM games"))
            print("  ✓ Deleted games")

            # Delete lobby members
            db.execute(text("DELETE FROM lobby_members"))
            print("  ✓ Deleted lobby members")

            # Delete lobbies
            db.execute(text("DELETE FROM lobbies"))
            print("  ✓ Deleted lobbies")

            # Delete friendships
            db.execute(text("DELETE FROM friendships"))
            print("  ✓ Deleted friendships")

            # Delete events (if exists)
            try:
                db.execute(text("DELETE FROM events"))
                print("  ✓ Deleted events")
            except Exception:
                pass  # Table might not exist

            db.commit()
            print("\n[STEP 2] Related data deleted successfully")
        except Exception as e:
            print(f"[ERROR] Error deleting related data: {e}")
            db.rollback()
            return

        # Now delete all users
        print("\n[STEP 3] Deleting all users...")
        try:
            delete_stmt = delete(User)
            result = db.execute(delete_stmt)
            db.commit()

            deleted_count = result.rowcount
            print(f"\n[SUCCESS] Successfully deleted {deleted_count} users")
            print("[INFO] All related data has also been deleted")

        except Exception as e:
            print(f"[ERROR] Error deleting users: {e}")
            import traceback

            traceback.print_exc()
            db.rollback()

    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback

        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    import sys

    confirm = "--confirm" in sys.argv
    asyncio.run(delete_all_users(confirm=confirm))
