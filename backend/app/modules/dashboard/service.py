import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import String, column, func, select, true, values
from sqlalchemy.sql import Select

from app.core.errors import AppError
from app.models.campaigns import Job
from app.models.operations import InsightSnapshot

ENGAGEMENT_METRICS = ("views", "reach", "likes", "comments", "shares", "saved")


class EngagementPeriod(StrEnum):
    TODAY = "today"
    YESTERDAY = "yesterday"
    MONTH = "month"
    CUSTOM = "custom"


@dataclass(frozen=True, slots=True)
class EngagementWindow:
    period: EngagementPeriod
    date_from: date
    date_to: date
    starts_at: datetime
    ends_at: datetime


def engagement_window(
    period: EngagementPeriod,
    timezone: str,
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    now: datetime | None = None,
) -> EngagementWindow:
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo("UTC")
    local_today = (now or datetime.now(UTC)).astimezone(zone).date()

    if period == EngagementPeriod.TODAY:
        first_day = last_day = local_today
    elif period == EngagementPeriod.YESTERDAY:
        first_day = last_day = local_today - timedelta(days=1)
    elif period == EngagementPeriod.MONTH:
        first_day = local_today.replace(day=1)
        last_day = local_today
    else:
        if date_from is None or date_to is None:
            raise AppError(
                "custom_period_dates_required",
                "Informe a data inicial e a data final do período personalizado.",
                status_code=422,
            )
        if date_from > date_to:
            raise AppError(
                "invalid_custom_period",
                "A data inicial não pode ser posterior à data final.",
                status_code=422,
            )
        if date_to > local_today:
            raise AppError(
                "future_custom_period",
                "O período personalizado não pode terminar no futuro.",
                status_code=422,
            )
        if (date_to - date_from).days > 365:
            raise AppError(
                "custom_period_too_long",
                "O período personalizado pode ter no máximo 366 dias.",
                status_code=422,
            )
        first_day, last_day = date_from, date_to

    starts_at = datetime.combine(first_day, time.min, tzinfo=zone).astimezone(UTC)
    ends_at = datetime.combine(last_day + timedelta(days=1), time.min, tzinfo=zone).astimezone(
        UTC
    )
    return EngagementWindow(period, first_day, last_day, starts_at, ends_at)


def engagement_metrics_statement(
    owner_id: uuid.UUID,
    starts_at: datetime,
    ends_at: datetime,
) -> Select[tuple[str, float | None, datetime | None]]:
    period_jobs = (
        select(Job.external_media_id.label("external_media_id"))
        .where(
            Job.owner_id == owner_id,
            Job.state == "succeeded",
            Job.external_media_id.is_not(None),
            Job.published_at >= starts_at,
            Job.published_at < ends_at,
        )
        .distinct()
        .subquery()
    )
    metric_names = (
        values(column("metric", String), name="engagement_metrics")
        .data([(metric,) for metric in ENGAGEMENT_METRICS])
        .cte("engagement_metrics")
    )
    latest_insight = (
        select(
            InsightSnapshot.value.label("value"),
            InsightSnapshot.captured_at.label("captured_at"),
        )
        .where(
            InsightSnapshot.owner_id == owner_id,
            InsightSnapshot.external_media_id == period_jobs.c.external_media_id,
            InsightSnapshot.metric == metric_names.c.metric,
        )
        .order_by(InsightSnapshot.captured_at.desc())
        .limit(1)
        .correlate(period_jobs, metric_names)
        .lateral("latest_insight")
    )
    return (
        select(
            metric_names.c.metric,
            func.sum(latest_insight.c.value).label("value"),
            func.max(latest_insight.c.captured_at).label("captured_at"),
        )
        .select_from(period_jobs)
        .join(metric_names, true())
        .outerjoin(latest_insight, true())
        .group_by(metric_names.c.metric)
    )
