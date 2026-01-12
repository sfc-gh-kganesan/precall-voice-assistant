from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

load_dotenv()


class ErrorResponse(BaseModel):
    error: str = Field(description="Error message describing what went wrong")
    detail: str | None = Field(default=None, description="Additional error details")


# Application metadata
VERSION = "1.0.0"
TITLE = "Knowledge Builder Service API"
DESCRIPTION = """
Knowledge Builder Service functions
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=TITLE,
    description=DESCRIPTION,
    version=VERSION,
    lifespan=lifespan,
    docs_url="/docs",
)

v1_router = APIRouter(prefix="/v1", tags=["v1"])


@app.get("/", tags=["System"], summary="Root endpoint")
async def index():
    """Root endpoint with API information."""
    return {
        "message": "Knowledge Builder Service API",
        "version": VERSION,
        "api_version": "v1",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["System"], summary="Health check")
async def health():
    """Health check endpoint for monitoring and load balancers."""
    return {"status": "healthy", "version": VERSION, "api_version": "v1"}


app.include_router(v1_router)


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    return JSONResponse(status_code=500, content={"error": "Internal server error", "detail": str(exc)})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True, log_level="info")
