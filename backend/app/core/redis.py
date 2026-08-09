from functools import lru_cache

from redis.asyncio import Redis

from app.core.config import settings


@lru_cache
def get_redis() -> Redis:
    return Redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
        health_check_interval=30,
    )


async def redis_ready() -> bool:
    try:
        return bool(await get_redis().ping())
    except Exception:
        return False


async def close_redis() -> None:
    client = get_redis()
    try:
        await client.aclose()
    finally:
        get_redis.cache_clear()
