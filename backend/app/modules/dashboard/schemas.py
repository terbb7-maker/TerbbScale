from datetime import date, datetime

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_accounts: int
    connected_accounts: int
    expired_accounts: int
    active_campaigns: int
    completed_campaigns: int
    publications_today: int
    publications_yesterday: int
    publications_7d: int
    publications_30d: int
    views: float | None
    likes: float | None
    comments: float | None
    shares: float | None
    saves: float | None
    engagement_rate: float | None
    engagement_period: str
    engagement_date_from: date
    engagement_date_to: date
    insights_status: str
    insights_updated_at: datetime | None
    queue_depth: int
    total_proxies: int
    online_proxies: int
    offline_proxies: int
    average_proxy_latency_ms: float | None
    accounts_using_proxy: int
    campaigns_using_proxy: int


class TimeSeriesPoint(BaseModel):
    day: date
    publications: int
    failures: int
    views: float | None = None


class UpcomingItem(BaseModel):
    job_id: str
    campaign_name: str
    account_username: str
    media_name: str
    scheduled_at: datetime
    state: str
