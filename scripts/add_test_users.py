#!/usr/bin/env python3
"""
Simple script to add test users
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


async def add_test_users():
    """Add 10 test users with complete information"""
    print("Starting to add test users...")

    # Get database session
    db = next(get_db())

    try:
        from src.user_service.models.user import User, UserRepository
        from sqlalchemy.exc import IntegrityError

        user_repo = UserRepository(db)
        total_users = 10

        # Prepare user data with email and password
        users_data = []
        for i in range(1, total_users + 1):
            username = f"player{i}"
            email = f"player{i}@test.com"

            users_data.append({"name": username, "email": email})

        # Insert users one by one to handle duplicates gracefully
        added_count = 0
        skipped_count = 0

        for user_data in users_data:
            try:
                # Check if user already exists by email
                from sqlalchemy import select

                stmt = select(User).where(User.email == user_data["email"])
                existing = db.execute(stmt).scalar_one_or_none()

                if existing:
                    print(f"[SKIP] User {user_data['email']} already exists")
                    skipped_count += 1
                    continue

                # Create user using repository method (which handles password hashing)
                await user_repo.create(
                    name=user_data["name"],
                    email=user_data["email"],
                    password="test123",  # Will be hashed by create method
                )
                added_count += 1
                print(
                    f"[SUCCESS] Added user: {user_data['name']} ({user_data['email']})"
                )

            except IntegrityError:
                print(
                    f"[SKIP] User {user_data['email']} already exists (integrity error)"
                )
                db.rollback()
                skipped_count += 1
                continue
            except Exception as e:
                print(f"[ERROR] Failed to add user {user_data['email']}: {e}")
                db.rollback()
                continue

        print(
            f"\n[SUMMARY] Successfully added {added_count} users, skipped {skipped_count} existing users"
        )
        print("[INFO] All users have password: test123")
        print("[INFO] Users: player1@test.com through player10@test.com")

    except Exception as e:
        print(f"[ERROR] Error adding users: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(add_test_users())
