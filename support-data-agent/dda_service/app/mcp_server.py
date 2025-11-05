"""
MCP Server for DDA Service

Converts the FastAPI application to an MCP server using FastMCP.
All REST API endpoints are automatically exposed as MCP tools.
"""

import logging

from fastmcp import FastMCP

from app.config import settings
from app.main import app as fastapi_app

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Convert FastAPI app to MCP server with authentication headers
mcp = FastMCP.from_fastapi(
    app=fastapi_app,
    name="DDA Diagnostic Service",
    httpx_client_kwargs={
        "headers": {
            "X-API-Key": settings.API_KEY,
        },
        "timeout": 30.0,
    },
)

logger.info("MCP server configured with authentication headers")

if __name__ == "__main__":
    # Run the MCP server with streamable-http transport
    # This makes it compatible with PydanticAI's MCPServerStreamableHTTP client
    print("Starting DDA MCP Server...")
    print("Server will be available at http://localhost:8000/mcp")
    print("\nAvailable tools will include:")
    print("  - Case operations (get_case, search_cases, get_case_queries)")
    print(
        "  - TSW diagnostics (locks, incidents, compilation, UDF, RBAC, auth, iceberg)"
    )
    print("  - Query analysis")
    print("  - Warehouse operations")
    print("  - Account operations")
    mcp.run(transport="streamable-http")
