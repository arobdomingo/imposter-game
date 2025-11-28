#!/usr/bin/env python3
"""
Script to delete test users (specifically the 20,000 test users created earlier)
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Set environment variable mapping
# If POSTGRES_HOST is 'db' (Docker service name), use localhost
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


async def delete_test_users():
    """Delete test users matching the pattern test_user_XXXXX"""
    print("Starting to delete test users...")
    print("WARNING: This will delete all users with names starting with 'test_user_'")

    # Get confirmation
    response = input("Are you sure you want to continue? (yes/no): ")
    if response.lower() != "yes":
        print("Cancelled.")
        return

    # Get database session
    db = next(get_db())

    try:
        from src.user_service.models.user import User
        from sqlalchemy import select, delete

        # Find all users matching the pattern
        stmt = select(User).where(User.name.like("test_user_%"))
        test_users = db.execute(stmt).scalars().all()

        total_count = len(test_users)

        if total_count == 0:
            print("[INFO] No test users found matching pattern 'test_user_%'")
            return

        print(f"[INFO] Found {total_count} test users to delete")

        # Delete in batches to avoid memory issues
        batch_size = 1000
        deleted_count = 0

        for i in range(0, total_count, batch_size):
            batch = test_users[i : i + batch_size]
            user_ids = [user.id for user in batch]

            try:
                # Delete users by ID
                delete_stmt = delete(User).where(User.id.in_(user_ids))
                result = db.execute(delete_stmt)
                db.commit()

                deleted_count += result.rowcount
                print(f"[PROGRESS] Deleted {deleted_count}/{total_count} users...")

            except Exception as e:
                print(f"[ERROR] Failed to delete batch: {e}")
                db.rollback()
                continue

        print(f"\n[SUMMARY] Successfully deleted {deleted_count} test users")

    except Exception as e:
        print(f"[ERROR] Error deleting users: {e}")
        import traceback

        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


async def delete_all_test_users_safe():
    """Delete all test users (test_user_* and player*) - safer version with preview"""
    print("Starting to delete test users...")

    # Get database session
    db = next(get_db())

    try:
        from src.user_service.models.user import User
        from sqlalchemy import select, delete

        # Find all test users (both test_user_* and player*)
        stmt = select(User).where(
            (User.name.like("test_user_%")) | (User.name.like("player%"))
        )
        test_users = db.execute(stmt).scalars().all()

        total_count = len(test_users)

        if total_count == 0:
            print("[INFO] No test users found")
            return

        print(f"\n[PREVIEW] Found {total_count} test users:")
        # Show first 10 as preview
        for i, user in enumerate(test_users[:10]):
            print(f"  - {user.name} ({user.email})")
        if total_count > 10:
            print(f"  ... and {total_count - 10} more")

        print("\nWARNING: This will delete ALL test users (test_user_* and player*)")
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() != "yes":
            print("Cancelled.")
            return

        # Delete in batches
        batch_size = 1000
        deleted_count = 0

        for i in range(0, total_count, batch_size):
            batch = test_users[i : i + batch_size]
            user_ids = [user.id for user in batch]

            try:
                delete_stmt = delete(User).where(User.id.in_(user_ids))
                result = db.execute(delete_stmt)
                db.commit()

                deleted_count += result.rowcount
                print(f"[PROGRESS] Deleted {deleted_count}/{total_count} users...")

            except Exception as e:
                print(f"[ERROR] Failed to delete batch: {e}")
                db.rollback()
                continue

        print(f"\n[SUMMARY] Successfully deleted {deleted_count} test users")

    except Exception as e:
        print(f"[ERROR] Error deleting users: {e}")
        import traceback

        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    import sys

    # Check command line argument
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        # Delete all test users (test_user_* and player*)
        asyncio.run(delete_all_test_users_safe())
    else:
        # Only delete test_user_* users (the 20,000 ones)
        asyncio.run(delete_test_users())
