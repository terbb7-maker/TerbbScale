import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
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


class Setting(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "settings"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    instagram_app_id: Mapped[str | None] = mapped_column(String(128))
    instagram_app_secret_ciphertext: Mapped[str | None] = mapped_column(Text)
    redirect_uri: Mapped[str | None] = mapped_column(Text)
    scopes: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        default=lambda: [
            "instagram_business_basic",
            "instagram_business_content_publish",
            "instagram_business_manage_insights",
        ],
        nullable=False,
    )
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    app_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    app_last_error: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (UniqueConstraint("owner_id", name="uq_settings_owner_id"),)


class Account(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "accounts"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    instagram_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(160))
    username: Mapped[str] = mapped_column(String(80), nullable=False)
    profile_picture_url: Mapped[str | None] = mapped_column(Text)
    account_type: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24), default="connected", nullable=False)
    health_status: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    health_confidence: Mapped[str] = mapped_column(String(16), default="unknown", nullable=False)
    health_source: Mapped[str | None] = mapped_column(String(32))
    health_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    health_last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    health_next_check_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    health_consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    health_error_code: Mapped[str | None] = mapped_column(String(64))
    health_error_subcode: Mapped[str | None] = mapped_column(String(64))
    health_message: Mapped[str | None] = mapped_column(Text)
    health_action_required: Mapped[str | None] = mapped_column(Text)
    granted_scopes: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error_code: Mapped[str | None] = mapped_column(String(96))
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    proxy_rotation_mode: Mapped[str] = mapped_column(String(16), default="fixed", nullable=False)
    proxy_rotation_every: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    proxy_rotation_counter: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    proxy_rotation_current_proxy_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("proxies.id", ondelete="SET NULL")
    )

    __table_args__ = (
        Index("ix_accounts_owner_status", "owner_id", "status"),
        Index(
            "ix_accounts_health_due",
            "health_next_check_at",
            "id",
            postgresql_where=removed_at.is_(None),
        ),
        Index(
            "ix_accounts_owner_health",
            "owner_id",
            "health_status",
            postgresql_where=removed_at.is_(None),
        ),
        Index(
            "uq_accounts_owner_instagram_active",
            "owner_id",
            "instagram_user_id",
            unique=True,
            postgresql_where=removed_at.is_(None),
        ),
    )


class Proxy(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "proxies"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    protocol: Mapped[str] = mapped_column(String(16), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    password_ciphertext: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(String(80))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="unknown", nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    last_check: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    public_ip: Mapped[str | None] = mapped_column(String(64))
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_proxies_owner_created", "owner_id", "created_at"),
        Index(
            "proxies_owner_active_idx",
            "owner_id",
            "created_at",
            postgresql_where=removed_at.is_(None),
        ),
        Index("ix_proxies_active_health", "is_active", "last_check", postgresql_where=is_active),
    )


class AccountProxy(Base, TimestampMixin):
    __tablename__ = "account_proxies"

    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), primary_key=True
    )
    proxy_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("proxies.id", ondelete="CASCADE"), primary_key=True
    )
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_selected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_account_proxies_proxy_id", "proxy_id"),
        Index(
            "ix_account_proxies_rotation",
            "account_id",
            "priority",
            "last_selected_at",
            postgresql_where=is_active,
        ),
    )


class Token(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "tokens"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    token_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    token_type: Mapped[str] = mapped_column(String(32), default="user", nullable=False)
    scopes: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, nullable=False)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refresh_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    __table_args__ = (
        Index("ix_tokens_account_active", "account_id", "revoked_at"),
        Index("ix_tokens_expiry_active", "expires_at", postgresql_where=revoked_at.is_(None)),
    )


class OAuthState(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "oauth_states"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    state_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    code_verifier_ciphertext: Mapped[str | None] = mapped_column(Text)
    redirect_after: Mapped[str | None] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_oauth_states_expiry", "expires_at"),)


class AccountHealthCheck(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "account_health_checks"

    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    details: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_account_health_account_checked", "account_id", "checked_at"),
        Index("account_health_owner_checked_idx", "owner_id", "checked_at"),
    )
