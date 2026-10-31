
import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import URL

# Alembic configuration.
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Project root: PROBENET/
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Load local environment variables.
load_dotenv(PROJECT_ROOT / ".env")

password = os.getenv("PROBENET_DB_PASSWORD")

if not password:
    raise RuntimeError(
        "PROBENET_DB_PASSWORD is missing. "
        "Set it in your local .env file."
    )

# Build a PostgreSQL connection URL.
database_url = URL.create(
    drivername="postgresql+psycopg",
    username="probenet",
    password=password,
    host="127.0.0.1",
    port=5434,
    database="probenet",
)

# SQLAlchemy model metadata will be added later.
target_metadata = None


def run_migrations_offline() -> None:
    """Generate SQL without connecting to PostgreSQL."""
    context.configure(
        url=database_url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the PostgreSQL database."""
    engine = create_engine(
        database_url,
        poolclass=pool.NullPool,
    )

    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
