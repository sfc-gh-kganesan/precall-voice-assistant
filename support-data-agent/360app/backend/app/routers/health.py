from datetime import datetime

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@router.get("/ready")
async def ready() -> dict:
    # Phase 0: assume ready without Snowflake check
    try:
        return {"status": "ready", "database": "skipped"}
    except Exception as exc:  # pragma: no cover
        raise HTTPException(503, f"Not ready: {exc}") from exc
