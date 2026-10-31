import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def get_engine() -> Engine:
    """Create the PostgreSQL database engine."""
    load_dotenv(PROJECT_ROOT / ".env")

    password = os.environ["PROBENET_DB_PASSWORD"]

    url = URL.create(
        drivername="postgresql+psycopg",
        username="probenet",
        password=password,
        host="127.0.0.1",
        port=5434,
        database="probenet",
    )

    return create_engine(url, pool_pre_ping=True)