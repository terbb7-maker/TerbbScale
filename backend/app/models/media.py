import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Media(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "media"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    original_name: Mapped[str] = mapped_column(String(512), nullable=False)
    display_name: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_bucket: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    media_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    thumbnail_key: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="processing", nullable=False)
    compatibility: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(Text)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_media_owner_created", "owner_id", "created_at"),
        Index("ix_media_owner_kind_status", "owner_id", "media_kind", "status"),
        Index(
            "ix_media_owner_hash_active",
            "owner_id",
            "content_hash",
            postgresql_where=deleted_at.is_(None),
        ),
        UniqueConstraint("owner_id", "storage_key", name="uq_media_owner_storage_key"),
    )


class CookieStoryPreset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "cookie_story_presets"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    media_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False
    )
    link_url: Mapped[str] = mapped_column(Text, nullable=False)
    link_title: Mapped[str | None] = mapped_column(String(80))

    __table_args__ = (
        UniqueConstraint("owner_id", name="uq_cookie_story_presets_owner_id"),
        Index("ix_cookie_story_presets_media_id", "media_id"),
        CheckConstraint(
            "link_url ~ '^https://[^[:space:]]+$'",
            name="https_link",
        ),
        CheckConstraint(
            "link_title is null or char_length(link_title) between 1 and 80",
            name="link_title_length",
        ),
    )


class MediaTag(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "media_tags"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    color: Mapped[str | None] = mapped_column(String(16))

    __table_args__ = (UniqueConstraint("owner_id", "name", name="uq_media_tags_owner_name"),)


class MediaTagLink(Base):
    __tablename__ = "media_tag_links"

    media_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("media_tags.id", ondelete="CASCADE"), primary_key=True
    )

    __table_args__ = (Index("ix_media_tag_links_tag_id", "tag_id"),)


class MediaVariant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "media_variants"

    owner_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    media_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False
    )
    variant_type: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    metadata_json: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict, nullable=False)

    __table_args__ = (Index("ix_media_variants_media_id", "media_id"),)


class UploadSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "upload_sessions"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    original_name: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    expected_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="created", nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_upload_sessions_owner_status", "owner_id", "status"),)
