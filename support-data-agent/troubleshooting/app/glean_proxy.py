"""
Glean MCP Proxy Server

A local FastMCP proxy that connects to the Glean MCP server with OAuth authentication.
This proxy handles the OAuth flow and exposes Glean's tools locally,
allowing PydanticAI agents to connect without OAuth complexity.

Usage:
    1. Start the proxy: uv run app/glean_proxy.py
    2. Complete OAuth flow in browser (opens automatically)
    3. Connect agents to http://localhost:8001/mcp
"""

import asyncio
import logging

from fastmcp import Client, FastMCP

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Glean MCP server URL
GLEAN_SERVER_URL = "https://snowflake-be.glean.com/mcp/default"

# Tools to exclude from the proxy (blacklist)
# Add tool names here that you don't want to expose
EXCLUDED_TOOLS = {
    "chat",
    # Add more tools to exclude here as needed
}

# Global client instance
glean_client = None


async def setup_glean_proxy():
    """
    Setup the Glean proxy by connecting to Glean with OAuth
    and creating a local server that wraps Glean tools.
    """
    global glean_client

    logger.info(f"Connecting to Glean at {GLEAN_SERVER_URL}")
    logger.info("OAuth authentication will open in your browser...")

    # Create FastMCP client with OAuth
    glean_client = Client(GLEAN_SERVER_URL, auth="oauth")

    # Enter the client context (this triggers OAuth flow)
    await glean_client.__aenter__()
    logger.info("✓ Connected to Glean successfully")

    # List available tools from Glean
    logger.info("Fetching tools from Glean...")
    tools_response = await glean_client.list_tools()
    print(tools_response)
    tools = tools_response.tools if hasattr(tools_response, "tools") else []

    logger.info(f"✓ Found {len(tools)} tools from Glean")

    # Create local FastMCP server
    proxy = FastMCP("Glean Proxy")

    # Dynamically create wrapper functions for each Glean tool
    excluded_count = 0
    for tool in tools:
        tool_name = tool.name

        # Skip excluded tools
        if tool_name in EXCLUDED_TOOLS:
            logger.info(f"  ⊗ Skipping excluded tool: {tool_name}")
            excluded_count += 1
            continue

        # Create a wrapper function that calls the Glean tool
        async def tool_wrapper(*args, _tool_name=tool_name, **kwargs):
            """Wrapper that forwards calls to Glean"""
            # Merge args and kwargs into a single dict for call_tool
            params = kwargs.copy()
            if args:
                # If positional args are provided, try to match them with input schema
                logger.warning(f"Positional args provided for {_tool_name}, using kwargs only")

            logger.info(f"Calling Glean tool: {_tool_name} with params: {params}")
            result = await glean_client.call_tool(_tool_name, params)

            # Extract text content from result
            if hasattr(result, "content") and result.content:
                content = result.content[0]
                if hasattr(content, "text"):
                    return content.text
                return str(content)
            return str(result)

        # Set function metadata
        tool_wrapper.__name__ = tool_name
        tool_wrapper.__doc__ = tool.description if hasattr(tool, "description") else f"Glean tool: {tool_name}"

        # Register the wrapper as a tool on the proxy
        proxy.tool(tool_wrapper)
        logger.info(f"  ✓ Registered tool: {tool_name}")

    logger.info(f"\nSummary: Registered {len(tools) - excluded_count} tools, excluded {excluded_count} tools")

    return proxy


def main():
    """Main entry point"""
    print("=" * 70)
    print("Glean MCP Proxy Server")
    print("=" * 70)
    print(f"\nConnecting to: {GLEAN_SERVER_URL}")
    print("Authentication: OAuth (browser-based)")
    print("\nStarting proxy server...")
    print("  Local URL: http://localhost:8001/mcp")
    print("\nNote: A browser window will open for OAuth authentication.")
    print("=" * 70)
    print()

    # Setup and run the proxy
    async def run_proxy():
        proxy = await setup_glean_proxy()
        logger.info("Starting HTTP server...")

        # Run the proxy on HTTP transport
        await proxy.run_async(transport="http", host="127.0.0.1", port=8001, path="/mcp")

    asyncio.run(run_proxy())


if __name__ == "__main__":
    main()
