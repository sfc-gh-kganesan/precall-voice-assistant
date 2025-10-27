"""Configuration management for the Support Data Agent backend."""

import os
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings


class SnowflakeSettings(BaseSettings):
    """
    Flexible Snowflake connection configuration.

    Automatically captures any environment variables starting with SNOWFLAKE_
    and passes them to the Snowflake connection. This supports all Snowflake
    authentication methods (password, key-pair, SSO, etc.) and connection parameters.
    """

    warehouse: str = "COMPUTE_WH"
    schema_name: str = Field(default="PUBLIC", alias="schema")

    model_config = {
        "env_prefix": "SNOWFLAKE_",
        "case_sensitive": False,
        "extra": "allow",
    }

    def get_connection_params(self) -> dict[str, Any]:
        params = {}
        supported_params = {"account", "user", "password", "database", "warehouse", "schema", "role"}

        for env_key, env_value in os.environ.items():
            if env_key.startswith("SNOWFLAKE_"):
                param_name = env_key[10:].lower()
                if param_name in supported_params:
                    params[param_name] = env_value

        return params


snowflake_settings = SnowflakeSettings()
