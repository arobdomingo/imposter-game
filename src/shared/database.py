import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load .env from project root
load_dotenv()

host = os.environ.get("POSTGRES_HOST", "localhost")
username = os.environ.get('POSTGRES_USER', 'group7')
password = os.environ.get('POSTGRES_PASSWORD', '123456789')

DATABASE_URL = f"postgresql+psycopg2://{username}:{password}@{host}:5432/postgres"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
