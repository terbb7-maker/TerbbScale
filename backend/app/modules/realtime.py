import asyncio
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.database import SessionFactory
from app.core.redis import get_redis
from app.core.security import verify_internal_payload
from app.models.identity import User

router = APIRouter(prefix="/ws", tags=["realtime"])


@router.websocket("/dashboard")
async def dashboard_events(websocket: WebSocket, ticket: str) -> None:
    try:
        payload = verify_internal_payload(ticket)
        if payload.get("purpose") != "dashboard-websocket":
            raise ValueError("Invalid ticket purpose")
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, TypeError, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    async with SessionFactory() as session:
        user = await session.get(User, user_id)
        if user is None or user.status != "active":
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

    await websocket.accept()
    pubsub = get_redis().pubsub()
    await pubsub.subscribe(f"user:{user_id}:events")
    try:
        await websocket.send_json({"event": "connected", "data": {}})
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15)
            if message and message.get("type") == "message":
                await websocket.send_text(message["data"])
            else:
                await websocket.send_json({"event": "heartbeat", "data": {}})
            await asyncio.sleep(0.1)
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        await pubsub.unsubscribe(f"user:{user_id}:events")
        await pubsub.aclose()
