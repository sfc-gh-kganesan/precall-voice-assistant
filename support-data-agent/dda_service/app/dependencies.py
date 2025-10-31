"""
Dependency injection for FastAPI endpoints.
Provides reusable dependencies for authentication, database connections, etc.
"""

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from typing import Optional

from app.config import settings

# API Key Security for MVP
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """
    Validate API key from request header.
    Simple authentication for MVP - will be replaced with OAuth2 + JWT in Phase 2.

    Args:
        api_key: API key from X-API-Key header

    Returns:
        str: Validated API key

    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key


# Database connection will be added in database.py
# async def get_db():
#     """Get database connection from pool"""
#     pass

# Cache client will be added in cache.py
# async def get_cache():
#     """Get cache client"""
#     pass
