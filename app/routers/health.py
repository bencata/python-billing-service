from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as aioredis
from app.database import get_db
from app.config import settings

router = APIRouter(tags=["Health"])

@router.get("/health", status_code=status.HTTP_200_OK)
def liveness_check():
    """
    Liveness probe to verify that the FastAPI process is running.
    """
    return {"status": "healthy"}

@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness probe that checks database and Redis connectivity.
    """
    db_ok = False
    redis_ok = False

    # 1. Check Database Connectivity
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        db_ok = False
        db_error = str(e)

    # 2. Check Redis Connectivity
    try:
        r = aioredis.from_url(settings.REDIS_URL, socket_timeout=2.0)
        await r.ping()
        await r.aclose()
        redis_ok = True
    except Exception as e:
        redis_ok = False
        redis_error = str(e)

    if not db_ok or not redis_ok:
        detail = {
            "status": "unhealthy",
            "database": "connected" if db_ok else f"disconnected ({db_error})",
            "redis": "connected" if redis_ok else f"disconnected ({redis_error})"
        }
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail
        )

    return {
        "status": "ready",
        "database": "connected",
        "redis": "connected"
    }
