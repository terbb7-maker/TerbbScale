import os
from datetime import timedelta

from sqlalchemy import or_, select, update

from app.core.config import settings
from app.core.database import SessionFactory
from app.models.campaigns import Campaign, Job
from app.models.instagram import Account
from app.models.operations import SchedulerState
from app.modules.accounts.health import BLOCKING_HEALTH_STATUSES
from app.modules.common import utcnow
from app.workers.tasks import (
    check_account_health_task,
    check_proxies_task,
    collect_insights_task,
    publish_job_task,
    renew_tokens_task,
)

SCHEDULER_NAME = "publication-dispatcher"


async def scheduler_cycle() -> int:
    now = utcnow()
    lease_owner = f"{os.uname().nodename}:{os.getpid()}"
    async with SessionFactory() as session:
        async with session.begin():
            state = await session.get(SchedulerState, SCHEDULER_NAME, with_for_update=True)
            if state is None:
                state = SchedulerState(name=SCHEDULER_NAME)
                session.add(state)
                await session.flush()
            if (
                state.lease_expires_at
                and state.lease_expires_at > now
                and state.lease_owner != lease_owner
            ):
                return 0
            state.lease_owner = lease_owner
            state.lease_expires_at = now + timedelta(seconds=55)
            state.last_started_at = now

        async with session.begin():
            due = list(
                (
                    await session.scalars(
                        select(Job)
                        .join(Campaign, Campaign.id == Job.campaign_id)
                        .join(Account, Account.id == Job.account_id)
                        .where(
                            Campaign.state.in_(["scheduled", "running"]),
                            Job.state.in_(["planned", "retry_scheduled"]),
                            Job.scheduled_at <= now + timedelta(seconds=60),
                            or_(Job.next_attempt_at.is_(None), Job.next_attempt_at <= now),
                            Account.removed_at.is_(None),
                            Account.health_status.notin_(tuple(BLOCKING_HEALTH_STATUSES)),
                        )
                        .order_by(
                            Job.priority,
                            Job.scheduled_at,
                            Job.rotation_slot,
                            Job.plan_position,
                            Job.id,
                        )
                        .limit(500)
                        .with_for_update(skip_locked=True)
                    )
                ).all()
            )
            for job in due:
                job.state = "queued"
                job.lease_owner = lease_owner
                job.lease_expires_at = now + timedelta(seconds=settings.JOB_LEASE_SECONDS)
                campaign = await session.get(Campaign, job.campaign_id)
                if campaign and campaign.state == "scheduled":
                    campaign.state = "running"
            state = await session.get(SchedulerState, SCHEDULER_NAME)
            if state:
                state.last_completed_at = utcnow()
                state.last_success_at = utcnow()
                state.lease_owner = None
                state.lease_expires_at = None
                state.metadata_json = {"dispatched": len(due)}

    for job in due:
        publish_job_task.apply_async(args=[str(job.id)], queue="publishing")
    return len(due)


async def recover_stale_jobs() -> int:
    now = utcnow()
    async with SessionFactory() as session:
        result = await session.execute(
            update(Job)
            .where(
                Job.state.in_(["queued", "publishing"]),
                Job.lease_expires_at < now,
                Job.external_media_id.is_(None),
            )
            .values(
                state="retry_scheduled",
                next_attempt_at=now + timedelta(seconds=30),
                lease_owner=None,
                lease_expires_at=None,
                last_error_class="stale_lease",
            )
        )
        await session.commit()
        return int(result.rowcount or 0)


async def enqueue_token_renewal() -> None:
    renew_tokens_task.apply_async(queue="maintenance")


async def enqueue_insight_collection() -> None:
    collect_insights_task.apply_async(queue="maintenance")


async def enqueue_proxy_health_check() -> None:
    check_proxies_task.apply_async(queue="maintenance")


async def enqueue_account_health_checks() -> int:
    now = utcnow()
    async with SessionFactory() as session:
        async with session.begin():
            accounts = list(
                (
                    await session.scalars(
                        select(Account)
                        .where(
                            Account.removed_at.is_(None),
                            Account.health_next_check_at <= now,
                        )
                        .order_by(Account.health_next_check_at, Account.id)
                        .limit(500)
                        .with_for_update(skip_locked=True)
                    )
                ).all()
            )
            for account in accounts:
                account.health_next_check_at = now + timedelta(minutes=10)
    for account in accounts:
        check_account_health_task.apply_async(
            args=[str(account.id), "scheduled"],
            queue="maintenance",
        )
    return len(accounts)
