"""Database configuration and session management."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from backend.models.base import Base

# Determine database type from environment
USE_SNOWFLAKE = os.getenv("USE_SNOWFLAKE", "false").lower() == "true"

if USE_SNOWFLAKE:
    # Snowflake connection via SQLAlchemy
    # Format: snowflake://<user>:<password>@<account>/<database>/<schema>?warehouse=<warehouse>&role=<role>
    SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
    SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
    SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
    SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE", "AGENTSIM_DB")
    SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
    SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
    SNOWFLAKE_ROLE = os.getenv("SNOWFLAKE_ROLE")

    DATABASE_URL = (
        f"snowflake://{SNOWFLAKE_USER}:{SNOWFLAKE_PASSWORD}@{SNOWFLAKE_ACCOUNT}/"
        f"{SNOWFLAKE_DATABASE}/{SNOWFLAKE_SCHEMA}?"
        f"warehouse={SNOWFLAKE_WAREHOUSE}&role={SNOWFLAKE_ROLE}"
    )

    engine = create_engine(DATABASE_URL, echo=False)
else:
    # Use SQLite for development
    # Use DATABASE_PATH env var or default to ./agentsim.db relative to working directory
    # For Docker: working dir is /app, so it becomes /app/agentsim.db
    # For local: set DATABASE_PATH in .env to use absolute path or run from project root
    DATABASE_PATH = os.getenv("DATABASE_PATH", "./agentsim.db")

    # Convert to absolute path to avoid issues with different working directories
    if not os.path.isabs(DATABASE_PATH):
        # If relative path, resolve it from current working directory
        DATABASE_PATH = os.path.abspath(DATABASE_PATH)

    DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # Needed for SQLite
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database (create tables)."""
    if USE_SNOWFLAKE:
        # Use Snowpark-based schema manager for Snowflake
        from backend.services.snowflake_schema import initialize_snowflake_schema

        print("Initializing Snowflake schema...")
        result = initialize_snowflake_schema()
        print(f"Snowflake schema initialized: {result}")
    else:
        # Use SQLAlchemy for SQLite
        print("Initializing SQLite schema...")
        Base.metadata.create_all(bind=engine)
        print("SQLite schema initialized")
