from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys
from dotenv import load_dotenv

# ---------------- Load .env ----------------
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ---------------- Add src to path ----------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# ---------------- Alembic config ----------------
config = context.config

section = config.config_ini_section
config.set_section_option(
    section, "DATABASE_HOST", os.environ.get("POSTGRES_HOST", "localhost")
)
config.set_section_option(
    section, "DATABASE_USER", os.environ.get("POSTGRES_USER", "user")
)
config.set_section_option(
    section, "DATABASE_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "password")
)
config.set_section_option(
    section, "DATABASE_NAME", os.environ.get("POSTGRES_DB", "postgres")
)

db_url = (
    f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}:"
    f"{os.environ['POSTGRES_PASSWORD']}@"
    f"{os.environ['POSTGRES_HOST']}:"
    f"{os.environ.get('POSTGRES_PORT', 5432)}/"
    f"{os.environ['POSTGRES_DB']}"
)
config.set_main_option("sqlalchemy.url", db_url)

# ---------------- Logging ----------------
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

from user_service import models

target_metadata = models.Base.metadata

# ---------------- Import shared Base ----------------
from user_service.models.user import Base  # Single shared Base

# ---------------- Target metadata ----------------
target_metadata = Base.metadata

# ---------------- Friendship ----------------
from user_service.models import friendship


# ---------------- Offline migrations ----------------
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


# ---------------- Online migrations ----------------
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
