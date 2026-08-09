import asyncio
import signal

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.database import close_database
from app.core.logging import configure_logging, logger
from app.core.redis import close_redis
from app.scheduler.engine import (
    enqueue_account_health_checks,
    enqueue_insight_collection,
    enqueue_proxy_health_check,
    enqueue_token_renewal,
    recover_stale_jobs,
    scheduler_cycle,
)


async def run() -> None:
    configure_logging()
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        scheduler_cycle,
        "interval",
        seconds=60,
        id="dispatch",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        recover_stale_jobs,
        "interval",
        minutes=2,
        id="recovery",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        enqueue_token_renewal,
        "interval",
        hours=6,
        id="token-renewal",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        enqueue_insight_collection,
        "interval",
        minutes=5,
        id="insights",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        enqueue_account_health_checks,
        "interval",
        minutes=1,
        id="account-health",
        max_instances=1,
        coalesce=True,
    )
    scheduler.add_job(
        enqueue_proxy_health_check,
        "interval",
        minutes=5,
        id="proxy-health",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    await scheduler_cycle()
    await enqueue_insight_collection()
    await enqueue_account_health_checks()
    await enqueue_proxy_health_check()
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    logger.info("scheduler_started")
    await stop.wait()
    scheduler.shutdown(wait=False)
    await close_database()
    await close_redis()


if __name__ == "__main__":
    asyncio.run(run())
