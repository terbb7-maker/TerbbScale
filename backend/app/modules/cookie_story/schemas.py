import uuid
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator


class CookieStoryPresetInput(BaseModel):
    media_id: uuid.UUID
    link_url: HttpUrl
    link_title: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("link_url")
    @classmethod
    def require_safe_https_link(cls, value: HttpUrl) -> HttpUrl:
        if value.scheme != "https":
            raise ValueError("O link do Story precisa usar HTTPS.")
        if value.username or value.password:
            raise ValueError("O link do Story não pode conter credenciais.")
        return value

    @field_validator("link_title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        return value.strip() if value else None


class CookieStoryPresetOut(BaseModel):
    id: uuid.UUID
    media_id: uuid.UUID
    media_name: str
    media_kind: str
    mime_type: str
    size_bytes: int
    width: int | None
    height: int | None
    duration_ms: int | None
    preview_url: str | None = None
    link_url: str
    link_title: str | None
    updated_at: datetime


class CookieStoryDeliveryOut(BaseModel):
    preset_id: uuid.UUID
    preset_version: str
    media_id: uuid.UUID
    media_url: str
    media_name: str
    media_kind: str
    mime_type: str
    size_bytes: int
    width: int
    height: int
    duration_ms: int | None
    link_url: str
    link_title: str | None
    expires_at: datetime
