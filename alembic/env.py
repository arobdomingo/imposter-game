from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

import os
import sys
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Add src/ to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

# Alembic Config object
config = context.config

# Inject environment variables into alembic.ini
section = config.config_ini_section

# Check if DATABASE_URL is provided (common in Render, Heroku, etc.)
database_url = os.environ.get("DATABASE_URL")
if database_url:
    # If DATABASE_URL is provided, use it directly
    # Convert postgresql:// to postgresql+psycopg2:// if needed
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    config.set_section_option(section, "sqlalchemy.url", database_url)
else:
    # Fall back to individual environment variables
    host = os.environ.get("POSTGRES_HOST", "localhost")
    # Don't use "db" as default - that's only for Docker Compose
    if host == "db" and not os.environ.get("POSTGRES_HOST"):
        host = "localhost"
    
    config.set_section_option(section, "DATABASE_HOST", host)
    config.set_section_option(
        section, "DATABASE_USER", os.environ.get("POSTGRES_USER", "user")
    )
    config.set_section_option(
        section, "DATABASE_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "password")
    )

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import metadata
from user_service.models.user import Base  # noqa: E402
import user_service.models.friendship  # noqa: F401,E402
import event_service.models.event  # noqa: F401,E402
import game_service.models  # noqa: F401,E402

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
