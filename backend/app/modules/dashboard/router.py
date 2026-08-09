from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.models.campaigns import Campaign, Job
from app.models.instagram import Account, AccountProxy, Proxy
from app.models.media import Media
from app.modules.auth.dependencies import ActiveUserDep, SessionDep
from app.modules.dashboard.schemas import DashboardSummary, TimeSeriesPoint, UpcomingItem
from app.modules.dashboard.service import (
    EngagementPeriod,
    engagement_metrics_statement,
    engagement_window,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
INSIGHTS_SCOPE = "instagram_business_manage_insights"


@router.get("/summary", response_model=DashboardSummary)
async def summary(
    user: ActiveUserDep,
    session: SessionDep,
    period: Annotated[EngagementPeriod, Query()] = EngagementPeriod.TODAY,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> DashboardSummary:
    now = datetime.now(UTC)
    window = engagement_window(
        period,
        user.timezone,
        date_from=date_from,
        date_to=date_to,
        now=now,
    )
    today_window = engagement_window(EngagementPeriod.TODAY, user.timezone, now=now)
    yesterday_window = engagement_window(EngagementPeriod.YESTERDAY, user.timezone, now=now)
    account_stats = (
        await session.execute(
            select(
                func.count(Account.id),
                func.count(Account.id).filter(Account.status == "connected"),
                func.count(Account.id).filter(Account.status.in_(["expired", "revoked"])),
            ).where(Account.owner_id == user.id, Account.removed_at.is_(None))
        )
    ).one()
    campaign_stats = (
        await session.execute(
            select(
                func.count(Campaign.id).filter(
                    Campaign.state.in_(["scheduled", "running", "paused"])
                ),
                func.count(Campaign.id).filter(
                    Campaign.state.in_(["completed", "completed_with_errors"])
                ),
            ).where(Campaign.owner_id == user.id)
        )
    ).one()
    publication_stats = (
        await session.execute(
            select(
                func.count(Job.id).filter(
                    Job.published_at >= today_window.starts_at,
                    Job.published_at < today_window.ends_at,
                ),
                func.count(Job.id).filter(
                    Job.published_at >= yesterday_window.starts_at,
                    Job.published_at < yesterday_window.ends_at,
                ),
                func.count(Job.id).filter(Job.published_at >= now - timedelta(days=7)),
                func.count(Job.id).filter(Job.published_at >= now - timedelta(days=30)),
                func.count(Job.id).filter(
                    Job.state.in_(["planned", "queued", "publishing", "retry_scheduled"])
                ),
            ).where(Job.owner_id == user.id)
        )
    ).one()
    proxy_stats = (
        await session.execute(
            select(
                func.count(Proxy.id),
                func.count(Proxy.id).filter(Proxy.status == "online"),
                func.count(Proxy.id).filter(Proxy.status == "offline"),
                func.avg(Proxy.latency_ms).filter(Proxy.status == "online"),
            ).where(Proxy.owner_id == user.id, Proxy.removed_at.is_(None))
        )
    ).one()
    accounts_using_proxy = await session.scalar(
        select(func.count(AccountProxy.account_id))
        .join(Account, Account.id == AccountProxy.account_id)
        .where(Account.owner_id == user.id, Account.removed_at.is_(None))
    )
    campaigns_using_proxy = await session.scalar(
        select(func.count(Campaign.id)).where(
            Campaign.owner_id == user.id,
            Campaign.proxy_mode != "none",
            Campaign.state.in_(["scheduled", "running", "paused"]),
        )
    )
    metric_rows = (
        await session.execute(
            engagement_metrics_statement(user.id, window.starts_at, window.ends_at)
        )
    ).all()
    metrics = {row.metric: float(row.value) for row in metric_rows if row.value is not None}
    insight_updates = [row.captured_at for row in metric_rows if row.captured_at is not None]
    insights_updated_at = max(insight_updates, default=None)
    published_media_count = await session.scalar(
        select(func.count(Job.id)).where(
            Job.owner_id == user.id,
            Job.state == "succeeded",
            Job.external_media_id.is_not(None),
            Job.published_at >= window.starts_at,
            Job.published_at < window.ends_at,
        )
    )
    publications_missing_permission = await session.scalar(
        select(func.count(Job.id))
        .join(Account, Account.id == Job.account_id)
        .where(
            Job.owner_id == user.id,
            Job.state == "succeeded",
            Job.external_media_id.is_not(None),
            Job.published_at >= window.starts_at,
            Job.published_at < window.ends_at,
            (
                ~Account.granted_scopes.contains([INSIGHTS_SCOPE])
                | (Account.last_error_code == "insights_permission_missing")
            ),
        )
    )
    if not published_media_count:
        insights_status = "no_publications"
    elif publications_missing_permission:
        insights_status = "permission_required"
    elif insights_updated_at is None:
        insights_status = "pending"
    else:
        insights_status = "available"
    reach = metrics.get("reach")
    interactions = sum(metrics.get(name, 0) for name in ("likes", "comments", "shares", "saved"))
    engagement = round(interactions / reach * 100, 2) if reach else None
    return DashboardSummary(
        total_accounts=account_stats[0],
        connected_accounts=account_stats[1],
        expired_accounts=account_stats[2],
        active_campaigns=campaign_stats[0],
        completed_campaigns=campaign_stats[1],
        publications_today=publication_stats[0],
        publications_yesterday=publication_stats[1],
        publications_7d=publication_stats[2],
        publications_30d=publication_stats[3],
        views=metrics.get("views"),
        likes=metrics.get("likes"),
        comments=metrics.get("comments"),
        shares=metrics.get("shares"),
        saves=metrics.get("saved"),
        engagement_rate=engagement,
        engagement_period=window.period.value,
        engagement_date_from=window.date_from,
        engagement_date_to=window.date_to,
        insights_status=insights_status,
        insights_updated_at=insights_updated_at,
        queue_depth=publication_stats[4],
        total_proxies=proxy_stats[0],
        online_proxies=proxy_stats[1],
        offline_proxies=proxy_stats[2],
        average_proxy_latency_ms=float(proxy_stats[3]) if proxy_stats[3] is not None else None,
        accounts_using_proxy=int(accounts_using_proxy or 0),
        campaigns_using_proxy=int(campaigns_using_proxy or 0),
    )


@router.get("/timeseries", response_model=list[TimeSeriesPoint])
async def timeseries(
    user: ActiveUserDep,
    session: SessionDep,
    days: int = Query(default=30, ge=7, le=90),
) -> list[TimeSeriesPoint]:
    since = datetime.now(UTC) - timedelta(days=days)
    day = func.date_trunc("day", func.coalesce(Job.published_at, Job.updated_at))
    rows = (
        await session.execute(
            select(
                day.label("day"),
                func.count(Job.id).filter(Job.state == "succeeded").label("publications"),
                func.count(Job.id)
                .filter(Job.state.in_(["failed_permanent", "dead_letter"]))
                .label("failures"),
            )
            .where(Job.owner_id == user.id, Job.updated_at >= since)
            .group_by(day)
            .order_by(day)
        )
    ).all()
    return [
        TimeSeriesPoint(
            day=row.day.date(),
            publications=row.publications,
            failures=row.failures,
        )
        for row in rows
    ]


@router.get("/upcoming", response_model=list[UpcomingItem])
async def upcoming(user: ActiveUserDep, session: SessionDep) -> list[UpcomingItem]:
    rows = (
        await session.execute(
            select(
                Job.id,
                Campaign.name,
                Account.username,
                Media.display_name,
                Job.scheduled_at,
                Job.state,
            )
            .join(Campaign, Campaign.id == Job.campaign_id)
            .join(Account, Account.id == Job.account_id)
            .join(Media, Media.id == Job.media_id)
            .where(
                Job.owner_id == user.id,
                Job.state.in_(["planned", "queued", "retry_scheduled"]),
            )
            .order_by(Job.scheduled_at)
            .limit(20)
        )
    ).all()
    return [
        UpcomingItem(
            job_id=str(row.id),
            campaign_name=row.name,
            account_username=row.username,
            media_name=row.display_name,
            scheduled_at=row.scheduled_at,
            state=row.state,
        )
        for row in rows
    ]
