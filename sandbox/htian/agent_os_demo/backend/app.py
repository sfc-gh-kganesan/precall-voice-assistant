import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException

from backend.models import (
    AddAgentRequest,
    ListAgentsRequest,
    build_agent_manifest_from_add_agent_request,
)
from backend.registry import add_agent, list_agents, search_agents
from backend.utils import _create_snowflake_session

load_dotenv()
VERSION = os.getenv("VERSION", "V0.1.0")
TITLE = os.getenv("TITLE", "Agent OS Demo")
DESCRIPTION = os.getenv("DESCRIPTION", "A demo of the Agent OS")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    print(f"🚀 {TITLE} v{VERSION} started")

    print("Initializing Snowflake session...")
    _create_snowflake_session()
    print("Snowflake session initialized")

    yield

    # Shutdown
    print("Shutting down...")


app = FastAPI(
    title=TITLE,
    description=DESCRIPTION,
    version=VERSION,
    docs_url="/docs",
    lifespan=lifespan,
)

v1_router = APIRouter(prefix="/v1", tags=["v1"])


@app.get("/", tags=["System"], summary="Root endpoint")
async def index():
    """Root endpoint with API information."""
    return {
        "message": TITLE,
        "version": VERSION,
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["System"], summary="Health check")
async def health():
    """Health check endpoint for monitoring and load balancers."""
    return {"status": "healthy", "version": VERSION}


# ============================================================================
# Agent Endpoints
# ============================================================================


def agent_query_sanity_check(total: int, offset: int) -> None:
    if total > 50:
        raise HTTPException(status_code=400, detail="Total must be less than 50")
    if offset < 0:
        raise HTTPException(status_code=400, detail="Offset must be greater than 0")


@v1_router.get("/agents/list", tags=["Agents"], summary="List agents")
async def list_agents_endpoint(total: int = 20, offset: int = 0):
    """List agents endpoint."""
    try:
        agent_query_sanity_check(total, offset)
        list_agents_request = ListAgentsRequest(total=total, offset=offset)
        return await list_agents(list_agents_request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {e}")


@v1_router.get("/agents/search", tags=["Agents"], summary="Search agents")
async def search_agents_endpoint(query: str, total: int = 20, offset: int = 0):
    """Search agents endpoint."""
    try:
        agent_query_sanity_check(total, offset)
        search_agents_request = ListAgentsRequest(search_text=query, limit=total, offset=offset)
        return await search_agents(search_agents_request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search agents: {e}")


@v1_router.post("/agents/add", tags=["Agents"], summary="Add agent")
async def add_agent_endpoint(request: AddAgentRequest):
    """Add agent endpoint."""
    try:
        agent_manifest = build_agent_manifest_from_add_agent_request(request)
        return await add_agent(agent_manifest)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add agent: {e}")


# ============================================================================
# Register API Router
# ============================================================================

app.include_router(v1_router)

# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", reload=True, log_level="info", port=8000)
