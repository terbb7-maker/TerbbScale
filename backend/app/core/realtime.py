import json
import uuid

from app.core.redis import get_redis


async def publish_user_event(
    user_id: uuid.UUID,
    event: str,
    data: dict[str, object] | None = None,
) -> bool:
    payload = json.dumps(
        {"event": event, "data": data or {}},
        separators=(",", ":"),
        default=str,
    )
    try:
        await get_redis().publish(f"user:{user_id}:events", payload)
    except Exception:
        return False
    return True
