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
config.set_section_option(section, "DATABASE_HOST", os.environ.get("POSTGRES_HOST"))
config.set_section_option(section, "DATABASE_USER", os.environ.get("POSTGRES_USER"))
config.set_section_option(
    section, "DATABASE_PASSWORD", os.environ.get("POSTGRES_PASSWORD")
)

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import metadata
from user_service.models.user import Base  # noqa: E402

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
