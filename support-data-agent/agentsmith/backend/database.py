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
    # Use DATABASE_PATH env var or default to ./agentsmith.db relative to working directory
    # For Docker: working dir is /app, so it becomes /app/agentsmith.db
    # For local: set DATABASE_PATH in .env to use absolute path or run from project root
    DATABASE_PATH = os.getenv("DATABASE_PATH", "./agentsmith.db")

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
    """Dependency for getting database session (SQLite for app metadata)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_snowflake_db() -> Generator[Session, None, None]:
    """Dependency for getting Snowflake database session for querying AGENT_TRACES.

    This always creates a Snowflake connection regardless of USE_SNOWFLAKE setting,
    since we need to query live conversation data from Snowflake.
    """
    # Get Snowflake credentials
    SNOWFLAKE_USER = os.getenv("SNOWFLAKE_USER")
    SNOWFLAKE_PASSWORD = os.getenv("SNOWFLAKE_PASSWORD")
    SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT")
    SNOWFLAKE_DATABASE = os.getenv("SNOWFLAKE_DATABASE", "AI_FDE")
    SNOWFLAKE_SCHEMA = os.getenv("SNOWFLAKE_SCHEMA", "CX360_DEMO")
    SNOWFLAKE_WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE")
    SNOWFLAKE_ROLE = os.getenv("SNOWFLAKE_ROLE")

    # Check if Snowflake is configured
    if not all(
        [
            SNOWFLAKE_USER,
            SNOWFLAKE_PASSWORD,
            SNOWFLAKE_ACCOUNT,
            SNOWFLAKE_WAREHOUSE,
            SNOWFLAKE_ROLE,
        ]
    ):
        # Return None if Snowflake is not configured - routes will handle this
        yield None
        return

    # Create Snowflake connection URL
    snowflake_url = (
        f"snowflake://{SNOWFLAKE_USER}:{SNOWFLAKE_PASSWORD}@{SNOWFLAKE_ACCOUNT}/"
        f"{SNOWFLAKE_DATABASE}/{SNOWFLAKE_SCHEMA}?"
        f"warehouse={SNOWFLAKE_WAREHOUSE}&role={SNOWFLAKE_ROLE}"
    )

    # Create a new engine and session for this request
    snowflake_engine = create_engine(snowflake_url, echo=False)
    SnowflakeSession = sessionmaker(
        autocommit=False, autoflush=False, bind=snowflake_engine
    )
    db = SnowflakeSession()

    try:
        yield db
    finally:
        db.close()
        snowflake_engine.dispose()


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
