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
host = os.environ.get('POSTGRES_HOST', 'localhost')
if host == 'db':
    host = 'localhost'

os.environ['DATABASE_HOST'] = host
os.environ['DATABASE_USER'] = os.environ.get('POSTGRES_USER', 'postgres')
os.environ['DATABASE_PASSWORD'] = os.environ.get('POSTGRES_PASSWORD', 'password')

print(f"Connecting to database: {host}:5432, user: {os.environ['DATABASE_USER']}")

# Add project root directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.shared.database import get_db  # noqa: E402

async def add_test_users():
    """Add 20,000 test users"""
    print("Starting to add test users...")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Batch insert user data
        batch_size = 1000  # Insert 1000 users per batch
        total_users = 20000
        
        for batch_start in range(1, total_users + 1, batch_size):
            batch_end = min(batch_start + batch_size - 1, total_users)
            
            # Prepare batch data
            users_data = []
            for i in range(batch_start, batch_end + 1):
                username = f"test_user_{i:05d}"
                users_data.append({"name": username})
            
            # Batch insert
            try:
                from sqlalchemy import insert
                from src.user_service.models.user import User
                
                stmt = insert(User)
                db.execute(stmt, users_data)
                db.commit()
                
                print(f"[SUCCESS] Added {batch_end} users...")
                
            except Exception as e:
                print(f"[ERROR] Batch insert failed: {e}")
                db.rollback()
                continue
        
        print("[SUCCESS] Successfully added 20,000 test users!")
        
    except Exception as e:
        print(f"[ERROR] Error adding users: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(add_test_users())
