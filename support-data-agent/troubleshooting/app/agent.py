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
SYSTEM_PROMPT = """You are a Snowflake Support Assistant. You help support engineers
investigate and troubleshoot customer issues using the DDA (Diagnostic Data Application) tools
and Glean enterprise search capabilities.

Your capabilities include:

**DDA Diagnostic Tools:**
- Analyzing Salesforce cases and associated queries
- Investigating query performance issues (locks, compilation, execution)
- Troubleshooting authentication and authorization problems (SAML, OAuth, RBAC)
- Examining warehouse performance and configuration
- Analyzing account-level metrics and parameters
- Reviewing existing Jira tickets related to customer problem

**Glean Knowledge Tools:**
- Searching internal Snowflake documentation and knowledge base
- Finding code examples and implementations
- Locating employee information and org structure
- reviewing Snowflake internal conversations for answer to similar problems or reports of similar issues
- Reading full document content

When investigating issues:
1. Start by gathering context (case details, query metadata)
2. Use appropriate diagnostic tools based on the issue type
3. Supplement with Glean search for documentation, procedures, or related information
4. Analyze the data and identify patterns or anomalies
5. Provide clear, actionable findings

Always be thorough but concise and not overly verbose. Format technical details clearly.
"""


def create_dda_agent(
    model_name: str = "claude-4-sonnet",
    mcp_server_url: str = "http://localhost:8000/mcp",
    glean_proxy_url: str = "http://localhost:8001/mcp",
) -> Agent:
    """
    Create a PydanticAI agent configured with DDA MCP tools and Glean search.
    Uses Snowflake Cortex as the LLM provider instead of OpenAI.

    Args:
        model_name: The Cortex model to use (e.g., 'claude-4-sonnet', 'mistral-large')
        mcp_server_url: URL of the DDA MCP server
        glean_proxy_url: URL of the Glean proxy server (set to None to disable Glean)

    Returns:
        Configured PydanticAI Agent with both DDA and Gelan toolsets
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
        max_retries=10,
        api_key=snowflake_password,
        base_url=f"https://{snowflake_account}.snowflakecomputing.com/api/v2/cortex/v1",
    )

    # Create OpenAI provider with the Snowflake client
    provider = OpenAIProvider(openai_client=client)

    # Use custom model that handles Snowflake response quirks
    model = SnowflakeCortexModel(model_name, provider=provider)

    # Connect to the DDA MCP server
    logger.info(f"Connecting to DDA MCP server at {mcp_server_url}")
    dda_server = MCPServerStreamableHTTP(mcp_server_url)

    # Build toolsets list
    toolsets = [dda_server]

    # Optionally connect to Glean proxy
    if glean_proxy_url:
        logger.info(f"Connecting to Glean proxy at {glean_proxy_url}")
        glean_server = MCPServerStreamableHTTP(glean_proxy_url)
        toolsets.append(glean_server)
        logger.info("✓ Agent configured with DDA + Glean toolsets")
    else:
        logger.info("✓ Agent configured with DDA toolset only")

    # Create agent with multiple toolsets
    agent = Agent(
        model=model,
        toolsets=toolsets,
        system_prompt=SYSTEM_PROMPT,
    )

    return agent


# Default agent instance
dda_agent = create_dda_agent()
