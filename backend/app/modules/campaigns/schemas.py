import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CampaignInput(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    caption: str | None = Field(default=None, max_length=2200)
    hashtags: list[str] = Field(default_factory=list, max_length=30)
    publication_type: str = Field(pattern=r"^(feed|reel|story)$")
    media_strategy: str = Field(pattern=r"^(same_media|sequential|random_without_replacement)$")
    account_ids: list[uuid.UUID] = Field(min_length=1, max_length=5000)
    media_ids: list[uuid.UUID] = Field(min_length=1, max_length=5000)
    posts_per_hour: int = Field(ge=1, le=1000)
    duration_hours: int = Field(ge=1, le=168)
    schedule_distribution: str = Field(default="even", pattern=r"^(even|burst|cooldown)$")
    post_cooldown_minutes: int = Field(default=1, ge=1, le=60)
    schedule_mode: str = Field(pattern=r"^(now|scheduled)$")
    starts_at: datetime | None = None
    timezone: str = Field(min_length=1, max_length=64)
    cover_mode: str = Field(default="automatic", pattern=r"^(automatic|custom)$")
    custom_cover_media_id: uuid.UUID | None = None
    proxy_mode: str = Field(
        default="none", pattern=r"^(none|fixed|rotate_per_post|rotate_every_n_posts)$"
    )
    proxy_id: uuid.UUID | None = None
    proxy_ids: list[uuid.UUID] = Field(default_factory=list, max_length=500)
    proxy_rotation_every: int = Field(default=1, ge=1, le=1000)
    allow_media_reuse: bool = False
    planning_seed: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")

    @model_validator(mode="after")
    def schedule_is_consistent(self) -> "CampaignInput":
        if self.schedule_mode == "scheduled" and self.starts_at is None:
            raise ValueError("starts_at is required for scheduled campaigns")
        if self.schedule_distribution != "cooldown" and self.post_cooldown_minutes != 1:
            raise ValueError("post_cooldown_minutes is only valid for cooldown distribution")
        if (
            self.schedule_distribution == "cooldown"
            and (self.posts_per_hour - 1) * self.post_cooldown_minutes > 60
        ):
            raise ValueError("O cooldown não comporta a quantidade de posts dentro de uma hora")
        if self.cover_mode == "custom" and self.custom_cover_media_id is None:
            raise ValueError("custom_cover_media_id is required for a custom cover")
        if self.cover_mode == "custom" and self.publication_type != "reel":
            raise ValueError("custom covers are supported only for reels")
        if self.proxy_mode == "fixed" and self.proxy_id is None:
            raise ValueError("proxy_id is required for a fixed proxy")
        if self.proxy_mode != "fixed" and self.proxy_id is not None:
            raise ValueError("proxy_id is only valid for a fixed proxy")
        if self.proxy_mode.startswith("rotate_") and not self.proxy_ids:
            raise ValueError("proxy_ids is required for rotating campaigns")
        if self.proxy_mode != "rotate_every_n_posts" and self.proxy_rotation_every != 1:
            raise ValueError("proxy_rotation_every is only valid for rotate_every_n_posts")
        return self


class CampaignOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    caption: str | None
    hashtags: list[str]
    publication_type: str
    media_strategy: str
    posts_per_hour: int
    duration_hours: int
    schedule_distribution: str
    post_cooldown_minutes: int
    schedule_mode: str
    starts_at: datetime | None
    timezone: str
    cover_mode: str
    proxy_mode: str
    proxy_id: uuid.UUID | None
    proxy_rotation_every: int
    allow_media_reuse: bool
    state: str
    current_version: int
    planned_count: int
    succeeded_count: int
    failed_count: int
    created_at: datetime
    updated_at: datetime


class PlanItem(BaseModel):
    position: int
    account_id: uuid.UUID
    account_username: str
    media_id: uuid.UUID
    media_name: str
    scheduled_at: datetime


class CampaignPreview(BaseModel):
    valid: bool
    errors: list[str]
    warnings: list[str]
    requested_jobs: int
    planned_jobs: int
    planning_seed: str | None
    items: list[PlanItem]


class CampaignAccountDetail(BaseModel):
    id: uuid.UUID
    position: int
    username: str
    display_name: str | None
    profile_picture_url: str | None
    status: str
    token_expires_at: datetime | None
    published_count: int
    last_published_at: datetime | None
    job_counts: dict[str, int]


class CampaignMediaDetail(BaseModel):
    id: uuid.UUID
    position: int
    display_name: str
    media_kind: str
    mime_type: str
    size_bytes: int
    duration_ms: int | None
    width: int | None
    height: int | None
    status: str
    failure_reason: str | None


class CampaignJobAttemptDetail(BaseModel):
    id: uuid.UUID
    attempt_number: int
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    request_operation: str
    response_status: int | None
    external_trace_id: str | None
    sanitized_response: dict[str, object] | None
    error_class: str | None
    retryable: bool
    proxy_id: uuid.UUID | None


class CampaignJobDetail(BaseModel):
    id: uuid.UUID
    state: str
    priority: int
    plan_position: int
    rotation_slot: int
    scheduled_at: datetime
    attempt_count: int
    next_attempt_at: datetime | None
    lease_expires_at: datetime | None
    published_at: datetime | None
    external_container_id: str | None
    external_media_id: str | None
    last_error_class: str | None
    last_error_message: str | None
    account_id: uuid.UUID
    account_username: str
    media_id: uuid.UUID
    media_name: str
    proxy_id: uuid.UUID | None
    proxy_name: str | None
    attempts: list[CampaignJobAttemptDetail]


class CampaignEventDetail(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID | None
    event_type: str
    status: str
    message: str | None
    details: dict[str, object]
    occurred_at: datetime
    duration_ms: int | None
    account_username: str | None
    media_name: str | None


class CampaignQueueSummary(BaseModel):
    total: int
    active: int
    finished: int
    progress_percent: int
    counts: dict[str, int]


class CampaignSchedulerDetail(BaseModel):
    status: str
    last_success_at: datetime | None
    last_error: str | None
    metadata: dict[str, object]


class CampaignDetail(CampaignOut):
    account_ids: list[uuid.UUID]
    media_ids: list[uuid.UUID]
    accounts: list[CampaignAccountDetail]
    media: list[CampaignMediaDetail]
    queue: CampaignQueueSummary
    jobs: list[CampaignJobDetail]
    jobs_truncated: bool
    events: list[CampaignEventDetail]
    events_truncated: bool
    scheduler: CampaignSchedulerDetail | None
    max_attempts: int
