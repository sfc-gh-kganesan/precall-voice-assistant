"""
Snowflake Cortex Model Wrapper for Pydantic AI

Handles Snowflake Cortex API response quirks (empty finish_reason and service_tier fields)
that cause validation errors with the OpenAI client's Pydantic models.

This is a shared utility that can be used by any agent that calls Snowflake Cortex
via the OpenAI-compatible API endpoint.
"""

from pydantic_ai.models.openai import OpenAIChatModel


class SnowflakeCortexModel(OpenAIChatModel):
    """Custom model that handles Snowflake Cortex API response quirks.

    Snowflake Cortex returns empty strings ('') for finish_reason and service_tier
    fields, but the OpenAI client expects specific enum values. This model patches
    the response before validation to prevent Pydantic validation errors.

    Usage:
        from backend.code_agent.snowflake_cortex_model import SnowflakeCortexModel
        from pydantic_ai.providers.openai import OpenAIProvider
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=snowflake_password,
            base_url=f"https://{account}.snowflakecomputing.com/api/v2/cortex/v1"
        )
        provider = OpenAIProvider(openai_client=client)
        model = SnowflakeCortexModel("claude-4-sonnet", provider=provider)
    """

    def _process_response(self, response):
        """Patch Snowflake's empty fields before validation.

        Converts empty strings to valid enum values:
        - finish_reason: '' → 'stop'
        - service_tier: '' → 'default'

        Args:
            response: Raw response from Snowflake Cortex API

        Returns:
            Processed response compatible with OpenAI client validation
        """
        response_dict = response.model_dump()

        # Fix empty finish_reason (convert '' to 'stop')
        if "choices" in response_dict:
            for choice in response_dict["choices"]:
                if choice.get("finish_reason") == "":
                    choice["finish_reason"] = "stop"

        # Fix empty service_tier (convert '' to 'default')
        if response_dict.get("service_tier") == "":
            response_dict["service_tier"] = "default"

        # Re-create response with fixed data
        from openai.types import chat

        fixed_response = chat.ChatCompletion.model_validate(response_dict)

        return super()._process_response(fixed_response)
