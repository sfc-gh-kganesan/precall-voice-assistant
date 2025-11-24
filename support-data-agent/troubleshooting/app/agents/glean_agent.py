"""
PydanticAI Agent for Glean MCP Server

A slimmed-down AI agent that connects to the Glean MCP server via a local proxy.
Uses Snowflake Cortex as the LLM provider.

Prerequisites:
    1. Start the Glean proxy server: uv run app/glean_proxy.py
    2. Complete OAuth flow in browser (opens automatically)
    3. Then run this agent
"""

import asyncio
import logging
import os
import sys

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
logging.basicConfig(level=logging.INFO)
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


# System prompt for the Glean agent
SYSTEM_PROMPT = """You are a helpful AI assistant with access to Glean tools.

Glean provides enterprise search and knowledge management capabilities.
Use the available tools to help answer questions and complete tasks.

When using tools:
1. Understand what the user is asking for
2. Use appropriate tools based on their descriptions
3. Analyze the results and provide clear answers
4. Be concise but thorough in your responses
"""


def create_glean_agent(
    model_name: str = "claude-4-sonnet",
    mcp_server_url: str = "http://localhost:8001/mcp",
) -> Agent:
    """
    Create a PydanticAI agent configured with Glean MCP tools.
    Uses Snowflake Cortex as the LLM provider.

    Args:
        model_name: The Cortex model to use (e.g., 'claude-4-sonnet', 'mistral-large')
        mcp_server_url: URL of the Glean MCP server

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

    # Connect to the local Glean proxy server
    # The proxy (glean_proxy.py) handles OAuth authentication with Glean
    logger.info(f"Connecting to Glean proxy at {mcp_server_url}")
    mcp_server = MCPServerStreamableHTTP(mcp_server_url)

    # Create agent with the MCP server as a toolset
    agent = Agent(
        model=model,
        toolsets=[mcp_server],
        system_prompt=SYSTEM_PROMPT,
    )

    return agent


async def test_agent(query: str = "What tools are available?"):
    """
    Simple test function to verify the agent works.

    Args:
        query: Question to ask the agent
    """
    print("=" * 70)
    print("Glean Agent - Standalone Test")
    print("=" * 70)
    print(f"\nQuery: {query}")
    print("\nNote: Make sure glean_proxy.py is running first!")
    print("      Run: uv run app/glean_proxy.py")
    print("\nConnecting to local Glean proxy...")

    try:
        agent = create_glean_agent()
        print("✓ Agent created successfully")
        print("\nRunning query...\n")

        # Run the query
        result = await agent.run(query)

        print("Response:")
        print("-" * 70)
        print(result.output)
        print("-" * 70)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        logger.exception("Failed to run agent")

        # Check if it's a connection error
        error_str = str(e)
        if "401" in error_str or "Unauthorized" in error_str:
            print("\n⚠️  Authentication Error:")
            print("   Make sure the Glean proxy is running with OAuth completed.")
            print("   Run: uv run app/glean_proxy.py")
        elif "Connection" in error_str or "refused" in error_str:
            print("\n⚠️  Connection Error:")
            print("   The Glean proxy doesn't appear to be running.")
            print("   Start it with: uv run app/glean_proxy.py")

        sys.exit(1)


if __name__ == "__main__":
    # Get query from command line or use default
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What tools are available?"

    # Run the test
    asyncio.run(test_agent(query))
