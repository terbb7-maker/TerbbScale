import time

from fastapi import Request
from fastapi.responses import ORJSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from app.core.logging import logger
from app.core.redis import get_redis


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: object, requests_per_minute: int = 180) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if request.url.path in {"/health/live", "/health/ready"}:
            return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        window = int(time.time() // 60)
        key = f"rate:{ip}:{window}"
        try:
            redis = get_redis()
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, 70)
            if count > self.requests_per_minute:
                return ORJSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "rate_limited",
                            "message": "Muitas requisições. Tente novamente em instantes.",
                            "details": [],
                            "request_id": getattr(request.state, "request_id", None),
                        }
                    },
                    headers={"Retry-After": "60"},
                )
        except Exception as exc:
            logger.warning("rate_limit_backend_unavailable", error=str(exc))
        return await call_next(request)
