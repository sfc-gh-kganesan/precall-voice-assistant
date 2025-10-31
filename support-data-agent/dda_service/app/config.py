"""
Application configuration using Pydantic BaseSettings.
Loads configuration from environment variables and .env files.
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Environment
    ENV: str = "local"  # local, dev, canary, prod

    # Service Configuration
    SERVICE_NAME: str = "fde-dda-service"
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"

    # CORS
    CORS_ORIGINS: List[str] = ["*"]

    # Snowflake Connection
    SNOWFLAKE_ACCOUNT: str
    SNOWFLAKE_USER: str
    SNOWFLAKE_PASSWORD: str
    SNOWFLAKE_WAREHOUSE: str = "DDA_WH"
    SNOWFLAKE_DATABASE: str = "SUPPORT"
    SNOWFLAKE_SCHEMA: str = "CXE"
    SNOWFLAKE_ROLE: str = "DDA_ROLE"

    # Authentication (Simple API Key for MVP)
    API_KEY: str = "change_me_in_production"

    # Query Execution
    QUERY_TIMEOUT_SECONDS: int = 300
    MAX_QUERY_RESULTS: int = 10000

    # In-Memory Cache (MVP)
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 900  # 15 minutes
    CACHE_MAX_SIZE: int = 1000

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
