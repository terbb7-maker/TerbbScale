import asyncio
import uuid
from collections.abc import Awaitable, Callable

from app.core.database import close_database, engine
from app.core.redis import close_redis, get_redis
from app.workers.account_health import check_account_health
from app.workers.celery_app import celery_app
from app.workers.insights import collect_recent_insights
from app.workers.maintenance import check_active_proxies, renew_expiring_tokens
from app.workers.media_processor import process_media
from app.workers.publisher import publish_job, record_worker_runtime_failure


async def _run_isolated[T](factory: Callable[[], Awaitable[T]]) -> T:
    # Celery prefork processes execute each task with asyncio.run(). Connections
    # pooled by a previous event loop cannot be reused by the next one.
    await engine.dispose(close=False)
    get_redis.cache_clear()
    try:
        return await factory()
    finally:
        try:
            await close_database()
        finally:
            await close_redis()


def run_async_task[T](factory: Callable[[], Awaitable[T]]) -> T:
    return asyncio.run(_run_isolated(factory))


@celery_app.task(name="postx.publish_job", acks_late=True)
def publish_job_task(job_id: str) -> None:
    parsed_job_id = uuid.UUID(job_id)
    try:
        completed = run_async_task(lambda: publish_job(parsed_job_id))
        if not completed:
            publish_job_task.apply_async(args=[job_id], countdown=5, queue="publishing")
    except Exception as exc:
        failure = exc
        run_async_task(lambda: record_worker_runtime_failure(parsed_job_id, failure))
        raise


@celery_app.task(name="postx.process_media", acks_late=True)
def process_media_task(media_id: str) -> None:
    parsed_media_id = uuid.UUID(media_id)
    run_async_task(lambda: process_media(parsed_media_id))


@celery_app.task(name="postx.renew_tokens")
def renew_tokens_task() -> int:
    return run_async_task(renew_expiring_tokens)


@celery_app.task(name="postx.collect_insights")
def collect_insights_task() -> int:
    return run_async_task(collect_recent_insights)


@celery_app.task(name="postx.check_proxies")
def check_proxies_task() -> int:
    return run_async_task(check_active_proxies)


@celery_app.task(name="postx.check_account_health")
def check_account_health_task(account_id: str, source: str = "scheduled") -> str:
    parsed_account_id = uuid.UUID(account_id)
    return run_async_task(lambda: check_account_health(parsed_account_id, source=source))
