from fastapi import APIRouter

from app.core.database import database_ready
from app.core.redis import redis_ready

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def ready() -> dict[str, object]:
    database, redis = await database_ready(), await redis_ready()
    return {
        "status": "ok" if database and redis else "degraded",
        "database": database,
        "redis": redis,
    }
