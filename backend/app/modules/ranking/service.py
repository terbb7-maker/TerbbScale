import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import String, case, column, func, or_, select, true, values
from sqlalchemy.sql import Select

from app.core.errors import AppError
from app.models.campaigns import Job
from app.models.identity import User
from app.models.operations import InsightSnapshot

RANKING_TIMEZONE = "America/Sao_Paulo"
RANKING_METRICS = ("views", "reach", "likes", "comments", "shares", "saved")
RANKING_LIMIT = 100


@dataclass(frozen=True, slots=True)
class MonthlyRankingWindow:
    month: str
    period_start: date
    period_end: date
    starts_at: datetime
    ends_at: datetime
    is_current_month: bool


def _next_month(value: date) -> date:
    return date(value.year + (value.month == 12), 1 if value.month == 12 else value.month + 1, 1)


def monthly_ranking_window(
    month: str | None,
    *,
    now: datetime | None = None,
) -> MonthlyRankingWindow:
    zone = ZoneInfo(RANKING_TIMEZONE)
    local_today = (now or datetime.now(UTC)).astimezone(zone).date()
    current_month = local_today.replace(day=1)
    try:
        selected_month = (
            datetime.strptime(f"{month}-01", "%Y-%m-%d").date()
            if month is not None
            else current_month
        )
    except ValueError as exc:
        raise AppError(
            "invalid_ranking_month",
            "Informe o mês no formato AAAA-MM.",
            status_code=422,
        ) from exc
    if selected_month > current_month:
        raise AppError(
            "future_ranking_month",
            "O ranking de um mês futuro ainda não está disponível.",
            status_code=422,
        )
    next_month = _next_month(selected_month)
    starts_at = datetime.combine(selected_month, time.min, tzinfo=zone).astimezone(UTC)
    ends_at = datetime.combine(next_month, time.min, tzinfo=zone).astimezone(UTC)
    return MonthlyRankingWindow(
        month=selected_month.strftime("%Y-%m"),
        period_start=selected_month,
        period_end=next_month - timedelta(days=1),
        starts_at=starts_at,
        ends_at=ends_at,
        is_current_month=selected_month == current_month,
    )


def ranking_score(
    *,
    publications: int | float,
    views: int | float,
    likes: int | float,
    comments: int | float,
    shares: int | float,
    saves: int | float,
    engagement_rate: int | float,
) -> float:
    return round(
        float(publications + views + likes + comments + shares + saves + engagement_rate),
        2,
    )


def monthly_ranking_statement(
    window: MonthlyRankingWindow,
    *,
    current_user_id: uuid.UUID,
    limit: int = RANKING_LIMIT,
) -> Select[Any]:
    publications = (
        select(
            Job.owner_id.label("user_id"),
            func.count(Job.id).label("publications"),
        )
        .where(
            Job.state == "succeeded",
            Job.published_at.is_not(None),
            Job.published_at >= window.starts_at,
            Job.published_at < window.ends_at,
        )
        .group_by(Job.owner_id)
        .cte("ranking_publications")
    )
    period_media = (
        select(
            Job.owner_id.label("user_id"),
            Job.external_media_id.label("external_media_id"),
        )
        .where(
            Job.state == "succeeded",
            Job.external_media_id.is_not(None),
            Job.published_at >= window.starts_at,
            Job.published_at < window.ends_at,
        )
        .distinct()
        .cte("ranking_media")
    )
    metric_names = (
        values(column("metric", String), name="ranking_metrics")
        .data([(metric,) for metric in RANKING_METRICS])
        .cte("ranking_metrics")
    )
    latest_snapshot = (
        select(
            func.greatest(InsightSnapshot.value, 0.0).label("value"),
        )
        .where(
            InsightSnapshot.owner_id == period_media.c.user_id,
            InsightSnapshot.external_media_id == period_media.c.external_media_id,
            InsightSnapshot.metric == metric_names.c.metric,
        )
        .order_by(InsightSnapshot.captured_at.desc(), InsightSnapshot.id.desc())
        .limit(1)
        .correlate(period_media, metric_names)
        .lateral("ranking_latest_snapshot")
    )
    metric_totals = (
        select(
            period_media.c.user_id,
            *(
                func.coalesce(
                    func.sum(
                        latest_snapshot.c.value
                    ).filter(
                        metric_names.c.metric == metric,
                    ),
                    0.0,
                ).label(metric)
                for metric in RANKING_METRICS
            ),
        )
        .select_from(period_media)
        .join(metric_names, true())
        .outerjoin(latest_snapshot, true())
        .group_by(period_media.c.user_id)
        .cte("ranking_metric_totals")
    )
    stats = (
        select(
            User.id.label("user_id"),
            func.coalesce(func.nullif(func.btrim(User.full_name), ""), "Usuário Terbb").label(
                "full_name"
            ),
            User.avatar_url,
            publications.c.publications,
            *(
                func.coalesce(metric_totals.c[metric], 0.0).label(metric)
                for metric in RANKING_METRICS
            ),
        )
        .join(publications, publications.c.user_id == User.id)
        .outerjoin(metric_totals, metric_totals.c.user_id == User.id)
        .where(User.status == "active", User.deleted_at.is_(None))
        .cte("ranking_stats")
    )
    interactions = stats.c.likes + stats.c.comments + stats.c.shares + stats.c.saved
    engagement_rate = case(
        (stats.c.reach > 0, interactions / stats.c.reach * 100.0),
        else_=0.0,
    )
    score = (
        stats.c.publications
        + stats.c.views
        + stats.c.likes
        + stats.c.comments
        + stats.c.shares
        + stats.c.saved
        + engagement_rate
    )
    ranked = (
        select(
            stats.c.user_id,
            stats.c.full_name,
            stats.c.avatar_url,
            stats.c.publications,
            stats.c.views,
            stats.c.likes,
            stats.c.comments,
            stats.c.shares,
            stats.c.saved.label("saves"),
            engagement_rate.label("engagement_rate"),
            score.label("score"),
            func.row_number()
            .over(
                order_by=(
                    score.desc(),
                    stats.c.views.desc(),
                    interactions.desc(),
                    stats.c.publications.desc(),
                    stats.c.user_id,
                )
            )
            .label("position"),
            func.count().over().label("total_participants"),
        )
        .cte("monthly_ranking")
    )
    return (
        select(ranked)
        .where(
            or_(
                ranked.c.position <= limit,
                ranked.c.user_id == current_user_id,
            )
        )
        .order_by(ranked.c.position)
    )
