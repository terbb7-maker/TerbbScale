import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class CampaignLog(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "campaign_logs"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL")
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("jobs.id", ondelete="SET NULL")
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("accounts.id", ondelete="SET NULL")
    )
    media_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("media.id", ondelete="SET NULL")
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)

    __table_args__ = (
        Index("ix_campaign_logs_owner_occurred", "owner_id", "occurred_at"),
        Index("ix_campaign_logs_campaign_occurred", "campaign_id", "occurred_at"),
        Index("ix_campaign_logs_status_occurred", "status", "occurred_at"),
    )


class SchedulerState(Base, TimestampMixin):
    __tablename__ = "scheduler"

    name: Mapped[str] = mapped_column(String(96), primary_key=True)
    lease_owner: Mapped[str | None] = mapped_column(String(128))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)


class AuditLog(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "audit_logs"

    owner_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(128))
    outcome: Mapped[str] = mapped_column(String(24), nullable=False)
    request_id: Mapped[str | None] = mapped_column(String(64))
    ip_prefix: Mapped[str | None] = mapped_column(String(64))
    before_json: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    after_json: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_audit_logs_owner_occurred", "owner_id", "occurred_at"),
        Index("ix_audit_logs_actor_occurred", "actor_id", "occurred_at"),
    )


class Notification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "notifications"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default="info", nullable=False)
    data: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_notifications_owner_read_created", "owner_id", "read_at", "created_at"),
    )


class InsightSnapshot(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "insight_snapshots"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    external_media_id: Mapped[str | None] = mapped_column(String(128))
    metric: Mapped[str] = mapped_column(String(96), nullable=False)
    value: Mapped[float | None] = mapped_column(Float)
    period: Mapped[str | None] = mapped_column(String(32))
    source_version: Mapped[str] = mapped_column(String(32), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    raw_metadata: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)

    __table_args__ = (
        Index("ix_insights_owner_metric_captured", "owner_id", "metric", "captured_at"),
        Index("ix_insights_media_metric_captured", "external_media_id", "metric", "captured_at"),
        Index(
            "insights_owner_media_metric_captured_idx",
            "owner_id",
            "external_media_id",
            "metric",
            "captured_at",
            "id",
            postgresql_include=["value"],
            postgresql_where=external_media_id.is_not(None)
            & metric.in_(["views", "reach", "likes", "comments", "shares", "saved"]),
        ),
    )


class OutboxEvent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "outbox_events"

    owner_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True))
    topic: Mapped[str] = mapped_column(String(128), nullable=False)
    aggregate_type: Mapped[str] = mapped_column(String(64), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index(
            "ix_outbox_unpublished",
            "created_at",
            postgresql_where=published_at.is_(None),
        ),
    )


class Plan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "plans"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(96), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price_monthly: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    limits: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class UserPlan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_plans"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("plans.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), default="active", nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    overrides: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)

    __table_args__ = (
        Index("ix_user_plans_user_status", "user_id", "status"),
        Index(
            "uq_user_plans_user_active",
            "user_id",
            unique=True,
            postgresql_where=status == "active",
        ),
    )
