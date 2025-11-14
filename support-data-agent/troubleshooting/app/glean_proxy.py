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
import os

from fastmcp import Client, FastMCP
from fastmcp.client.auth import OAuth
from starlette.responses import JSONResponse

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Glean MCP server URL
GLEAN_SERVER_URL = "https://snowflake-be.glean.com/mcp/default"

# OAuth port configuration for Docker + socat setup
OAUTH_INTERNAL_PORT = int(
    os.getenv("OAUTH_INTERNAL_PORT", "8091")
)  # Where FastMCP binds
OAUTH_PUBLIC_PORT = int(
    os.getenv("OAUTH_PUBLIC_PORT", "8090")
)  # Where browser connects


class PatchedOAuth(OAuth):
    """
    Patched OAuth that uses different ports for internal binding vs external redirect.

    This allows Docker + socat setup where:
    - FastMCP binds callback server to 127.0.0.1:8091 (OAUTH_INTERNAL_PORT)
    - Browser redirects to localhost:8090 (OAUTH_PUBLIC_PORT)
    - socat forwards 0.0.0.0:8090 -> 127.0.0.1:8091

    The trick: Pass public_port as callback_port so parent __init__ uses it for redirect_uri,
    then change self.redirect_port back to internal port for actual callback server binding.
    """

    def __init__(self, *args, internal_port=None, public_port=None, **kwargs):
        # Store ports
        self._internal_port = internal_port or OAUTH_INTERNAL_PORT
        self._public_port = public_port or OAUTH_PUBLIC_PORT

        # Pass public port as callback_port so parent uses it for redirect_uri
        kwargs["callback_port"] = self._public_port

        # Initialize parent with public port
        super().__init__(*args, **kwargs)

        # Now switch redirect_port to internal port for callback server binding
        self.redirect_port = self._internal_port

        logger.info(
            f"🔧 PatchedOAuth: redirect_uri uses port {self._public_port}, callback server uses port {self._internal_port}"
        )


# Tools to exclude from the proxy (blacklist)
# Add tool names here that you don't want to expose
EXCLUDED_TOOLS = {
    "chat",
    # Add more tools to exclude here as needed
}

# Global client instance
glean_client = None


def create_tool_wrapper(tool_name: str, input_schema: dict, glean_client):
    """
    Dynamically create a wrapper function with explicit parameters from JSON schema.

    This function generates Python code for a wrapper that matches the tool's input schema,
    then executes it to create the actual function.
    """
    # Extract properties and required fields from schema
    properties = input_schema.get("properties", {})
    required_fields = set(input_schema.get("required", []))

    # Build function parameters and extract parameter names
    param_signatures = []
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

        # Add parameter with type hint
        if param_name in required_fields:
            param_signatures.append(f"{param_name}: {type_hint}")
        else:
            param_signatures.append(f"{param_name}: {type_hint} = None")

        # Store just the parameter name for later use
        param_names.append(param_name)

    # Generate function code
    param_str = ", ".join(param_signatures)

    # Build parameter collection code
    param_collection = "\n".join(
        f"    if {name} is not None:\n        params['{name}'] = {name}"
        for name in param_names
    )

    func_code = f'''
async def tool_wrapper({param_str}):
    """Wrapper that forwards calls to Glean tool: {tool_name}"""
    # Collect all provided parameters
    params = {{}}
{param_collection}

    # Call the Glean tool
    result = await glean_client.call_tool("{tool_name}", params)

    # Extract text content from result
    if hasattr(result, "content") and result.content:
        content = result.content[0]
        if hasattr(content, "text"):
            return content.text
        return str(content)
    return str(result)
'''

    # Execute the code to create the function
    local_vars = {"glean_client": glean_client}
    exec(func_code, local_vars)
    wrapper = local_vars["tool_wrapper"]

    return wrapper


async def setup_glean_proxy():
    """
    Setup the Glean proxy by connecting to Glean with OAuth
    and creating a local server that wraps Glean tools.
    """
    global glean_client

    logger.info(f"Connecting to Glean at {GLEAN_SERVER_URL}")
    logger.info("OAuth authentication will open in your browser...")

    # Configure OAuth with Docker + socat port setup
    # - Internal port 8091: Where FastMCP binds callback server (localhost only)
    # - Public port 8090: Where browser redirects (socat forwards to 8091)
    oauth_config = PatchedOAuth(
        mcp_url=GLEAN_SERVER_URL,
        internal_port=OAUTH_INTERNAL_PORT,  # FastMCP callback server binding
        public_port=OAUTH_PUBLIC_PORT,  # Browser redirect (for redirect_uri)
        client_name="DDA Glean Proxy",
    )

    # Create FastMCP client with patched OAuth
    glean_client = Client(GLEAN_SERVER_URL, auth=oauth_config)

    # Enter the client context (this triggers OAuth flow)
    await glean_client.__aenter__()
    logger.info("✓ Connected to Glean successfully")

    # List available tools from Glean
    logger.info("Fetching tools from Glean...")
    tools_response = await glean_client.list_tools()

    # Handle both list response and object with .tools attribute
    if isinstance(tools_response, list):
        tools = tools_response
    elif hasattr(tools_response, "tools"):
        tools = tools_response.tools
    else:
        tools = []

    logger.info(f"✓ Found {len(tools)} tools from Glean")

    # Create local FastMCP server
    proxy = FastMCP("Glean Proxy")

    # Add health check endpoint
    @proxy.custom_route("/health", ["GET"])
    async def health_check(request):
        """Health check endpoint for Docker health checks"""
        return JSONResponse({"status": "healthy", "service": "Glean Proxy"})

    # Dynamically create wrapper functions for each Glean tool
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
        tool_wrapper = create_tool_wrapper(tool_name, input_schema, glean_client)

        # Set function metadata
        tool_wrapper.__name__ = tool_name
        tool_wrapper.__doc__ = (
            tool.description
            if hasattr(tool, "description")
            else f"Glean tool: {tool_name}"
        )

        # Register the wrapper as a tool on the proxy
        proxy.tool(tool_wrapper)
        logger.info(f"  ✓ Registered tool: {tool_name}")

    logger.info(
        f"\nSummary: Registered {len(tools) - excluded_count} tools, excluded {excluded_count} tools"
    )

    # Debug: Print all available routes
    logger.info("=" * 70)
    logger.info("DEBUG: Available routes on Glean proxy:")
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
        await proxy.run_async(transport="http", host="0.0.0.0", port=8001, path="/mcp")

    asyncio.run(run_proxy())


if __name__ == "__main__":
    main()
