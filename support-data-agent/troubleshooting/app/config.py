"""
Application configuration using Pydantic BaseSettings.
Loads configuration from environment variables and .env files.
"""

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # JIRA Integration (Optional)
    JIRA_ENABLED: bool = False  # Disabled by default
    JIRA_ACCOUNT: str = "snowflakecomputing"
    JIRA_USER: str = ""
    JIRA_API_TOKEN: str = ""
    JIRA_PROJECT: str = "SNOW"
    JIRA_MAX_RESULTS: int = 50
    JIRA_CACHE_TTL_SECONDS: int = 300  # 5 minutes

    # Agent Memory Management
    CONVERSATION_HISTORY_LIMIT: int = 10  # Max messages to keep per conversation

    # Cortex Search Service (Snowflake Documentation)
    # Uses same SNOWFLAKE_ACCOUNT and SNOWFLAKE_PASSWORD as LLM calls
    CORTEX_SEARCH_SERVICE: str = "CKE_SNOWFLAKE_DOCS_SERVICE"
    CORTEX_SEARCH_DATABASE: str = "CORTEX_KNOWLEDGE_EXTENSION_SNOWFLAKE_DOCUMENTATION"
    CORTEX_SEARCH_SCHEMA: str = "SHARED"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # Allow extra fields from .env without validation errors
    )


# Global settings instance
settings = Settings()
