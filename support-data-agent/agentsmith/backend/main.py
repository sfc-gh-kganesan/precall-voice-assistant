"""FastAPI application for AgentSmith."""

import logging
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import init_db
from backend.api.routes import (
    projects,
    simulations,
    conversations,
    insights,
    project_metrics,
    project_conversations,
    project_insights,
)

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Create FastAPI app
app = FastAPI(
    title="AgentSmith",
    description="Chatbot conversation analysis and optimization platform",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(project_metrics.router, prefix="/api/projects", tags=["metrics"])
app.include_router(
    project_conversations.router, prefix="/api/projects", tags=["conversations"]
)
app.include_router(project_insights.router, prefix="/api/projects", tags=["insights"])
app.include_router(simulations.router, prefix="/api/simulations", tags=["simulations"])
app.include_router(insights.router, prefix="/api/simulations", tags=["insights"])
app.include_router(conversations.router, prefix="/api", tags=["conversations"])


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "AgentSim API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080, reload=True)
