"""
GitHub MCP Proxy Server

A local FastMCP proxy that connects to the GitHub MCP server with PAT authentication.
This proxy exposes GitHub's tools locally, allowing Claude Agent SDK agents to connect.

Usage:
    1. Set GITHUB_TOKEN in .env file with your GitHub Personal Access Token
    2. Start the proxy: uv run agentsim/backend/code_agent/github_proxy.py
    3. Connect agents to http://localhost:8003/mcp

Prerequisites:
    - GitHub Personal Access Token (PAT) with repo access
    - Add to .env: GITHUB_TOKEN=ghp_xxxxx
"""

import asyncio
import logging
import os

from dotenv import load_dotenv
from fastmcp import Client, FastMCP
from starlette.responses import JSONResponse

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GitHub MCP server URL
GITHUB_SERVER_URL = "https://api.githubcopilot.com/mcp/"


# GitHub toolsets to enable (default configuration)
# See: https://github.com/github/github-mcp-server#available-toolsets
GITHUB_TOOLSETS = os.getenv(
    "GITHUB_TOOLSETS",
    "context,repos,issues,pull_requests",  # Default toolsets for code recommendations
).split(",")

# Tools to exclude from the proxy (blacklist)
# Add tool names here that you don't want to expose
EXCLUDED_TOOLS = {
    # Add tools to exclude here as needed
}

# Global client instance
github_client = None


def create_tool_wrapper(tool_name: str, input_schema: dict, github_client):
    """
    Dynamically create a wrapper function with explicit parameters from JSON schema.

    This function generates Python code for a wrapper that matches the tool's input schema,
    then executes it to create the actual function.
    """
    # Extract properties and required fields from schema
    properties = input_schema.get("properties", {})
    required_fields = set(input_schema.get("required", []))

    # Separate required and optional parameters
    required_params = []
    optional_params = []
    param_names = []

    for param_name, param_schema in properties.items():
        param_type = param_schema.get("type", "string")

        # Map JSON schema types to Python type hints
        type_hint = {
            "string": "str",
            "number": "float",
            "integer": "int",
            "boolean": "bool",
            "array": "list",
            "object": "dict",
        }.get(param_type, "str")

        # Sort into required vs optional
        if param_name in required_fields:
            required_params.append(f"{param_name}: {type_hint}")
        else:
            optional_params.append(f"{param_name}: {type_hint} = None")

        # Store parameter name for collection code
        param_names.append(param_name)

    # Build function signature: required params first, then optional
    param_signatures = required_params + optional_params
    param_str = ", ".join(param_signatures)

    # Build parameter collection code
    param_collection = "\n".join(
        f"    if {name} is not None:\n        params['{name}'] = {name}"
        for name in param_names
    )

    func_code = f'''
async def tool_wrapper({param_str}):
    """Wrapper that forwards calls to GitHub tool: {tool_name}"""
    # Collect all provided parameters
    params = {{}}
{param_collection}

    # Call the GitHub tool
    result = await github_client.call_tool("{tool_name}", params)

    # Extract content from result (CallToolResult dataclass)
    # result.content is a list[mcp.types.ContentBlock]
    # GitHub MCP returns file content as resource type, not text type
    if result.content:
        # Iterate through all content blocks to find the resource
        for content_block in result.content:
            # Check for resource type (GitHub MCP file content)
            # Resource blocks have: type='resource', resource.text contains actual content
            if hasattr(content_block, 'type') and content_block.type == 'resource':
                if hasattr(content_block, 'resource'):
                    resource = content_block.resource
                    if hasattr(resource, 'text'):
                        logger.info(f"[{tool_name}] Extracted content from resource block (length: {{len(resource.text)}})")
                        return resource.text

            # Fallback: check for text type with actual content
            # Skip generic success messages from GitHub MCP
            if hasattr(content_block, 'text'):
                text = content_block.text
                # Return text if it's not just a success message
                if text and not text.startswith("successfully downloaded"):
                    logger.info(f"[{tool_name}] Extracted content from text block (length: {{len(text)}})")
                    return text

        # If we only found success message, return it (for debugging)
        content_block = result.content[0]
        if hasattr(content_block, 'text'):
            logger.warning(f"[{tool_name}] Only found success message, no resource block")
            return content_block.text

        # Last resort fallback
        return str(content_block)

    return str(result)
'''

    # Execute the code to create the function
    local_vars = {"github_client": github_client, "logger": logger}
    exec(func_code, local_vars)
    wrapper = local_vars["tool_wrapper"]

    return wrapper


async def setup_github_proxy():
    """
    Setup the GitHub proxy by connecting to GitHub with PAT authentication
    and creating a local server that wraps GitHub tools.
    """
    global github_client

    # Get GitHub token from environment
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise ValueError(
            "GITHUB_TOKEN must be set in environment. "
            "Get a PAT from https://github.com/settings/tokens and add to .env file."
        )

    logger.info(f"Connecting to GitHub MCP at {GITHUB_SERVER_URL}")
    logger.info("Authenticating with GitHub Personal Access Token...")

    # Create FastMCP client with PAT authentication using config format
    # FastMCP requires configuration dictionary for HTTP servers with custom headers
    config = {
        "mcpServers": {
            "github": {
                "url": GITHUB_SERVER_URL,
                "headers": {"Authorization": f"Bearer {github_token}"},
            }
        }
    }
    github_client = Client(config)

    # Enter the client context
    await github_client.__aenter__()
    logger.info("✓ Connected to GitHub MCP successfully")

    # List available tools from GitHub
    logger.info("Fetching tools from GitHub MCP...")
    tools_response = await github_client.list_tools()

    # Handle both list response and object with .tools attribute
    if isinstance(tools_response, list):
        tools = tools_response
    elif hasattr(tools_response, "tools"):
        tools = tools_response.tools
    else:
        tools = []

    logger.info(f"✓ Found {len(tools)} tools from GitHub MCP")

    # Create local FastMCP server
    proxy = FastMCP("GitHub Proxy")

    # Add health check endpoint
    @proxy.custom_route("/health", ["GET"])
    async def health_check(request):
        """Health check endpoint for Docker health checks"""
        return JSONResponse({"status": "healthy", "service": "GitHub Proxy"})

    # Dynamically create wrapper functions for each GitHub tool
    excluded_count = 0
    for tool in tools:
        tool_name = tool.name

        # Skip excluded tools
        if tool_name in EXCLUDED_TOOLS:
            logger.info(f"  ⊗ Skipping excluded tool: {tool_name}")
            excluded_count += 1
            continue

        # Get the tool's input schema
        input_schema = tool.inputSchema if hasattr(tool, "inputSchema") else {}

        # Create wrapper function with explicit parameters from schema
        tool_wrapper = create_tool_wrapper(tool_name, input_schema, github_client)

        # Set function metadata
        tool_wrapper.__name__ = tool_name
        tool_wrapper.__doc__ = (
            tool.description
            if hasattr(tool, "description")
            else f"GitHub tool: {tool_name}"
        )

        # Register the wrapper as a tool on the proxy
        proxy.tool(tool_wrapper)
        logger.info(f"  ✓ Registered tool: {tool_name}")

    logger.info(
        f"\nSummary: Registered {len(tools) - excluded_count} tools, excluded {excluded_count} tools"
    )

    # Debug: Print all available routes
    logger.info("=" * 70)
    logger.info("DEBUG: Available routes on GitHub proxy:")
    if hasattr(proxy, "app") and hasattr(proxy.app, "routes"):
        for route in proxy.app.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                logger.info(f"  Route: {route.path} - Methods: {route.methods}")
            elif hasattr(route, "path"):
                logger.info(f"  Route: {route.path}")
    logger.info("=" * 70)

    return proxy


def main():
    """Main entry point"""
    print("=" * 70)
    print("GitHub MCP Proxy Server")
    print("=" * 70)
    print(f"\nConnecting to: {GITHUB_SERVER_URL}")
    print("Authentication: Personal Access Token (PAT)")
    print(f"\nEnabled toolsets: {', '.join(GITHUB_TOOLSETS)}")
    print("\nStarting proxy server...")
    print(f"  Local URL: http://localhost:{os.getenv('SERVER_PORT', '8003')}/mcp")
    print("\nNote: Ensure GITHUB_TOKEN is set in your .env file.")
    print("=" * 70)
    print()

    # Setup and run the proxy
    async def run_proxy():
        proxy = await setup_github_proxy()
        logger.info("Starting HTTP server...")

        # Run the proxy on HTTP transport
        # Port can be configured via SERVER_PORT environment variable (default: 8003)
        server_port = int(os.getenv("SERVER_PORT", "8003"))
        await proxy.run_async(
            transport="http", host="0.0.0.0", port=server_port, path="/mcp"
        )

    asyncio.run(run_proxy())


if __name__ == "__main__":
    main()
