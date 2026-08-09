from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.modules.auth.dependencies import ActiveUserDep, SessionDep
from app.modules.ranking.schemas import MonthlyRankingEntry, MonthlyRankingOut
from app.modules.ranking.service import (
    RANKING_TIMEZONE,
    monthly_ranking_statement,
    monthly_ranking_window,
    ranking_score,
)

router = APIRouter(prefix="/ranking", tags=["ranking"])


def _number(value: object) -> float:
    return round(float(value or 0), 2)


@router.get("/monthly", response_model=MonthlyRankingOut)
async def monthly_ranking(
    user: ActiveUserDep,
    session: SessionDep,
    month: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")] = None,
) -> MonthlyRankingOut:
    generated_at = datetime.now(UTC)
    window = monthly_ranking_window(month, now=generated_at)
    rows = (
        await session.execute(
            monthly_ranking_statement(window, current_user_id=user.id)
        )
    ).mappings().all()
    entries: list[MonthlyRankingEntry] = []
    for row in rows:
        publications = int(row["publications"] or 0)
        views = _number(row["views"])
        likes = _number(row["likes"])
        comments = _number(row["comments"])
        shares = _number(row["shares"])
        saves = _number(row["saves"])
        engagement_rate = _number(row["engagement_rate"])
        entries.append(
            MonthlyRankingEntry(
                position=int(row["position"]),
                user_id=row["user_id"],
                full_name=str(row["full_name"]),
                avatar_url=row["avatar_url"],
                is_current_user=row["user_id"] == user.id,
                score=ranking_score(
                    publications=publications,
                    views=views,
                    likes=likes,
                    comments=comments,
                    shares=shares,
                    saves=saves,
                    engagement_rate=engagement_rate,
                ),
                publications=publications,
                views=views,
                likes=likes,
                comments=comments,
                shares=shares,
                saves=saves,
                engagement_rate=engagement_rate,
            )
        )
    return MonthlyRankingOut(
        month=window.month,
        period_start=window.period_start,
        period_end=window.period_end,
        timezone=RANKING_TIMEZONE,
        is_current_month=window.is_current_month,
        generated_at=generated_at,
        total_participants=int(rows[0]["total_participants"]) if rows else 0,
        entries=entries,
    )
