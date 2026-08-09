import uuid
from datetime import date, datetime

from pydantic import BaseModel


class MonthlyRankingEntry(BaseModel):
    position: int
    user_id: uuid.UUID
    full_name: str
    avatar_url: str | None
    is_current_user: bool
    score: float
    publications: int
    views: float
    likes: float
    comments: float
    shares: float
    saves: float
    engagement_rate: float


class MonthlyRankingOut(BaseModel):
    month: str
    period_start: date
    period_end: date
    timezone: str
    is_current_month: bool
    generated_at: datetime
    total_participants: int
    entries: list[MonthlyRankingEntry]
