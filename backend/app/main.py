from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.core.config import settings
from app.core.database import close_database
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.core.rate_limit import RateLimitMiddleware
from app.core.redis import close_redis
from app.modules.accounts.router import router as accounts_router
from app.modules.admin.router import router as admin_router
from app.modules.auth.router import router as auth_router
from app.modules.campaigns.router import router as campaigns_router
from app.modules.cookie_story.router import router as cookie_story_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.health import router as health_router
from app.modules.logs.router import router as logs_router
from app.modules.media.router import router as media_router
from app.modules.notifications.router import router as notifications_router
from app.modules.proxies.router import router as proxies_router
from app.modules.ranking.router import router as ranking_router
from app.modules.realtime import router as realtime_router
from app.modules.settings.router import router as settings_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    yield
    await close_database()
    await close_redis()


app = FastAPI(
    title="PostX API",
    version="0.1.0",
    default_response_class=ORJSONResponse,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)
install_error_handlers(app)

for router in (
    auth_router,
    accounts_router,
    cookie_story_router,
    media_router,
    campaigns_router,
    dashboard_router,
    logs_router,
    notifications_router,
    proxies_router,
    ranking_router,
    realtime_router,
    settings_router,
    admin_router,
):
    app.include_router(router, prefix="/api/v1")
app.include_router(health_router)
