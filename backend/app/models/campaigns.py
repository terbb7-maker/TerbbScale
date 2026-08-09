import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Campaign(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "campaigns"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    caption: Mapped[str | None] = mapped_column(Text)
    hashtags: Mapped[list[str]] = mapped_column(ARRAY(String(128)), default=list, nullable=False)
    publication_type: Mapped[str] = mapped_column(String(16), nullable=False)
    media_strategy: Mapped[str] = mapped_column(String(40), nullable=False)
    posts_per_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    schedule_distribution: Mapped[str] = mapped_column(String(16), default="even", nullable=False)
    post_cooldown_minutes: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    schedule_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    cover_mode: Mapped[str] = mapped_column(String(16), default="automatic", nullable=False)
    custom_cover_media_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("media.id", ondelete="SET NULL")
    )
    proxy_mode: Mapped[str] = mapped_column(String(16), default="none", nullable=False)
    proxy_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("proxies.id", ondelete="RESTRICT")
    )
    proxy_rotation_every: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    allow_media_reuse: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    planned_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    succeeded_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_campaigns_owner_state_created", "owner_id", "state", "created_at"),
        Index("ix_campaigns_state_starts", "state", "starts_at"),
        Index(
            "ix_campaigns_owner_proxy",
            "owner_id",
            "proxy_mode",
            postgresql_where=proxy_mode != "none",
        ),
    )


class CampaignVersion(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "campaign_versions"

    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    random_seed: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("campaign_id", "version", name="uq_campaign_versions_campaign_version"),
        Index("ix_campaign_versions_owner_id", "owner_id"),
    )


class CampaignAccount(Base):
    __tablename__ = "campaign_accounts"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)

    __table_args__ = (Index("ix_campaign_accounts_account_id", "account_id"),)


class CampaignMedia(Base):
    __tablename__ = "campaign_media"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True
    )
    media_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("media.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)

    __table_args__ = (Index("ix_campaign_media_media_id", "media_id"),)


class CampaignProxy(Base):
    __tablename__ = "campaign_proxies"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), primary_key=True
    )
    proxy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("proxies.id", ondelete="RESTRICT"), primary_key=True
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False)


class CampaignProxyAssignment(Base):
    __tablename__ = "campaign_proxy_assignments"

    campaign_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("campaign_versions.id", ondelete="CASCADE"), primary_key=True
    )
    rotation_slot: Mapped[int] = mapped_column(Integer, primary_key=True)
    proxy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("proxies.id", ondelete="RESTRICT"), nullable=False
    )
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Job(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "jobs"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    campaign_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("campaign_versions.id", ondelete="RESTRICT"), nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False
    )
    media_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("media.id", ondelete="RESTRICT"), nullable=False
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state: Mapped[str] = mapped_column(String(32), default="planned", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    plan_position: Mapped[int] = mapped_column(BigInteger, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    lease_owner: Mapped[str | None] = mapped_column(String(128))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_container_id: Mapped[str | None] = mapped_column(String(128))
    external_media_id: Mapped[str | None] = mapped_column(String(128))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_class: Mapped[str | None] = mapped_column(String(96))
    last_error_message: Mapped[str | None] = mapped_column(Text)
    proxy_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("proxies.id", ondelete="SET NULL")
    )
    rotation_slot: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        CheckConstraint("plan_position >= 0", name="jobs_plan_position_nonnegative"),
        UniqueConstraint(
            "campaign_version_id",
            "plan_position",
            name="uq_jobs_campaign_version_plan_position",
        ),
        Index("ix_jobs_state_scheduled", "state", "scheduled_at"),
        Index("ix_jobs_account_scheduled", "account_id", "scheduled_at"),
        Index("ix_jobs_campaign_state", "campaign_id", "state"),
        Index(
            "jobs_owner_published_media_idx",
            "owner_id",
            "published_at",
            postgresql_include=["external_media_id"],
            postgresql_where=(state == "succeeded")
            & published_at.is_not(None)
            & external_media_id.is_not(None),
        ),
        Index(
            "jobs_published_owner_ranking_idx",
            "published_at",
            "owner_id",
            postgresql_include=["external_media_id"],
            postgresql_where=(state == "succeeded") & published_at.is_not(None),
        ),
        Index(
            "ix_jobs_due",
            "scheduled_at",
            "priority",
            postgresql_where=state.in_(["planned", "retry_scheduled"]),
        ),
    )


class JobAttempt(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "job_attempts"

    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    request_operation: Mapped[str] = mapped_column(String(64), nullable=False)
    response_status: Mapped[int | None] = mapped_column(Integer)
    external_trace_id: Mapped[str | None] = mapped_column(String(128))
    sanitized_response: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    error_class: Mapped[str | None] = mapped_column(String(96))
    retryable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    proxy_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("proxies.id", ondelete="SET NULL")
    )

    __table_args__ = (
        UniqueConstraint("job_id", "attempt_number", name="uq_job_attempts_job_number"),
        Index("ix_job_attempts_owner_started", "owner_id", "started_at"),
    )
