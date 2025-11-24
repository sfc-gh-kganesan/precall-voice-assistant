"""
MCP Server for DDA Service

Converts the FastAPI application to an MCP server using FastMCP.
All REST API endpoints are automatically exposed as MCP tools.
"""

import logging

from fastmcp import FastMCP
from starlette.responses import JSONResponse

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


# Add health check endpoint for Docker health checks
@mcp.custom_route("/health", ["GET"])
async def health_check(request):
    """Health check endpoint for Docker"""
    return JSONResponse(
        {
            "status": "healthy",
            "service": "DDA Diagnostic Service",
        }
    )


logger.info("MCP server configured with authentication headers")

# Debug: Print all available routes after MCP server creation
logger.info("=" * 70)
logger.info("DEBUG: Available routes after FastMCP.from_fastapi():")
if hasattr(mcp, "app"):
    app = mcp.app
    if hasattr(app, "routes"):
        for route in app.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                logger.info(f"  Route: {route.path} - Methods: {route.methods}")
            elif hasattr(route, "path"):
                logger.info(f"  Route: {route.path}")
    else:
        logger.info("  No 'routes' attribute found on mcp.app")
else:
    logger.info("  No 'app' attribute found on mcp")
logger.info("=" * 70)

if __name__ == "__main__":
    # Run the MCP server with streamable-http transport
    # This makes it compatible with PydanticAI's MCPServerStreamableHTTP client
    print("Starting DDA MCP Server...")
    print("Server will be available at http://0.0.0.0:8000/mcp")
    print("\nAvailable tools will include:")
    print("  - Case operations (get_case, search_cases, get_case_queries)")
    print(
        "  - TSW diagnostics (locks, incidents, compilation, UDF, RBAC, auth, iceberg)"
    )
    print("  - Query analysis")
    print("  - Warehouse operations")
    print("  - Account operations")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
