"""Configuration management for the Support Data Agent backend."""

from pydantic import Field
from pydantic_settings import BaseSettings


class SnowflakeSettings(BaseSettings):
    """Snowflake connection configuration."""

    account: str
    user: str
    password: str
    warehouse: str = "COMPUTE_WH"
    database: str
    schema_name: str = Field(default="PUBLIC", alias="schema")
    role: str | None = None

    model_config = {
        "env_prefix": "SNOWFLAKE_",
        "case_sensitive": False,
        "extra": "ignore",
    }

    def get_connection_params(self) -> dict:
        params = {
            "account": self.account,
            "user": self.user,
            "password": self.password,
            "warehouse": self.warehouse,
            "database": self.database,
            "schema": self.schema_name,
        }
        return params


# Global settings instance
snowflake_settings = SnowflakeSettings()
