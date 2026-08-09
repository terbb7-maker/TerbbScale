import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UploadCreate(BaseModel):
    original_name: str = Field(min_length=1, max_length=512)
    mime_type: str = Field(pattern=r"^(image|video)/")
    size_bytes: int = Field(gt=0, le=1_073_741_824)


class UploadOut(BaseModel):
    id: uuid.UUID
    bucket: str
    storage_key: str
    expires_at: datetime


class UploadComplete(BaseModel):
    storage_key: str


class MediaPreviewOut(BaseModel):
    url: str
    expires_at: datetime


class MediaPreviewBatchInput(BaseModel):
    media_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)


class MediaPreviewItem(BaseModel):
    media_id: uuid.UUID
    url: str | None


class MediaPreviewBatchOut(BaseModel):
    previews: list[MediaPreviewItem]
    expires_at: datetime


class MediaBulkRemoveInput(BaseModel):
    media_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)


class MediaBulkRemoveOut(BaseModel):
    removed: int


class MediaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_name: str
    display_name: str
    storage_key: str
    mime_type: str
    media_kind: str
    size_bytes: int
    duration_ms: int | None
    width: int | None
    height: int | None
    content_hash: str | None
    thumbnail_key: str | None
    status: str
    compatibility: dict[str, object]
    failure_reason: str | None
    uploaded_at: datetime
    created_at: datetime


class MediaUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=512)
    tag_ids: list[uuid.UUID] | None = None


class MediaTagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")


class MediaTagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    color: str | None
    created_at: datetime
