"""
PydanticAI Agent for DDA Service

An AI agent that uses the DDA MCP server tools to help support engineers
diagnose Snowflake customer issues. Uses Snowflake Cortex as the LLM provider.
"""

import logging
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types import chat
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)


class SnowflakeCortexModel(OpenAIChatModel):
    """Custom model that handles Snowflake Cortex API response quirks"""

    def _process_response(self, response):
        # Patch Snowflake's empty fields before validation
        response_dict = response.model_dump()

        # Fix empty finish_reason
        if "choices" in response_dict:
            for choice in response_dict["choices"]:
                if choice.get("finish_reason") == "":
                    choice["finish_reason"] = "stop"

        # Fix empty service_tier
        if response_dict.get("service_tier") == "":
            response_dict["service_tier"] = "default"

        # Re-create response with fixed data
        fixed_response = chat.ChatCompletion.model_validate(response_dict)

        # Let parent process the fixed response
        return super()._process_response(fixed_response)


# System prompt for the agent
SYSTEM_PROMPT = """You are a Snowflake Support Diagnostic Assistant. You help support engineers
investigate and troubleshoot customer issues using the DDA (Diagnostic Data Application) tools.

Your capabilities include:
- Analyzing Salesforce cases and associated queries
- Investigating query performance issues (locks, compilation, execution)
- Troubleshooting authentication and authorization problems (SAML, OAuth, RBAC)
- Examining warehouse performance and configuration
- Analyzing account-level metrics and parameters

When investigating issues:
1. Start by gathering context (case details, query metadata)
2. Use appropriate diagnostic tools based on the issue type
3. Analyze the data and identify patterns or anomalies
4. Provide clear, actionable findings

Always be thorough but concise and not overly verbose. Format technical details clearly.
"""


def create_dda_agent(
    model_name: str = "claude-4-sonnet",
    mcp_server_url: str = "http://localhost:8000/mcp",
) -> Agent:
    """
    Create a PydanticAI agent configured with DDA MCP tools.
    Uses Snowflake Cortex as the LLM provider instead of OpenAI.

    Args:
        model_name: The Cortex model to use (e.g., 'claude-4-sonnet', 'mistral-large')
        mcp_server_url: URL of the DDA MCP server

    Returns:
        Configured PydanticAI Agent
    """
    # Setup OpenAI-compatible client for Snowflake Cortex
    snowflake_account = os.getenv("SNOWFLAKE_ACCOUNT")
    snowflake_password = os.getenv("SNOWFLAKE_PASSWORD")

    if not snowflake_account or not snowflake_password:
        raise ValueError(
            "SNOWFLAKE_ACCOUNT and SNOWFLAKE_PASSWORD must be set in environment"
        )

    # Create client pointing to Snowflake Cortex API
    client = AsyncOpenAI(
        max_retries=3,
        api_key=snowflake_password,
        base_url=f"https://{snowflake_account}.snowflakecomputing.com/api/v2/cortex/v1",
    )

    # Create OpenAI provider with the Snowflake client
    provider = OpenAIProvider(openai_client=client)

    # Use custom model that handles Snowflake response quirks
    model = SnowflakeCortexModel(model_name, provider=provider)

    # Connect to the MCP server
    mcp_server = MCPServerStreamableHTTP(mcp_server_url)

    # Create agent with the MCP server as a toolset
    agent = Agent(
        model=model,
        toolsets=[mcp_server],
        system_prompt=SYSTEM_PROMPT,
    )

    return agent


# Default agent instance
dda_agent = create_dda_agent()
