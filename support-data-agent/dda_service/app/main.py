"""
FastAPI application entry point for FDE DDA Service.
Frontend-Decoupled Diagnostic Data Application API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import logging

from app.config import settings
from app.api.v1.router import api_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="FDE DDA Service",
    description="Frontend-Decoupled Diagnostic Data Application API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Middleware configuration
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health")
async def health_check():
    """
    Health check endpoint for load balancers and monitoring.
    Returns service status and version information.
    """
    return {
        "status": "healthy",
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "environment": settings.ENV,
    }


@app.get("/ready")
async def readiness_check():
    """
    Readiness check - verifies service dependencies are available.
    Returns 200 if ready to serve traffic, 503 otherwise.
    """
    # TODO: Add Snowflake connection check in database layer
    return {
        "status": "ready",
        "dependencies": {
            "snowflake": "not_checked",  # Will implement in database.py
            "cache": "in_memory",
        },
    }


@app.on_event("startup")
async def startup_event():
    """Initialize resources on application startup"""
    logger.info(f"Starting {settings.SERVICE_NAME} in {settings.ENV} environment")
    logger.info("API documentation available at /api/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup resources on application shutdown"""
    logger.info(f"Shutting down {settings.SERVICE_NAME}")
