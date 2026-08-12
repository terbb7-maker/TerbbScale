import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

StoryFontFamily = Literal[
    "Inter",
    "Roboto",
    "Poppins",
    "Montserrat",
    "Bebas Neue",
    "Playfair Display",
    "Merriweather",
    "Pacifico",
    "DancingScript",
    "Anton",
    "Lora",
    "Great Vibes",
]

STORY_COLORS = {
    "rgba(0, 0, 0, 1)",
    "rgba(65, 174, 69, 1)",
    "rgba(0, 212, 255, 1)",
    "rgba(53, 141, 255, 1)",
    "rgba(115, 0, 255, 1)",
    "rgba(255, 255, 255, 1)",
    "rgba(255, 192, 10, 1)",
    "rgba(255, 129, 0, 1)",
    "rgba(255, 49, 49, 1)",
    "rgba(255, 101, 195, 1)",
}
STORY_DEFAULT_TEXT_COLOR = "#ffffff"
STORY_DEFAULT_BACKGROUND_COLOR = "rgba(0, 0, 0, 0.6)"


class CookieStoryStickerStyle(BaseModel):
    sticker_x: float = Field(default=0.5, ge=0, le=1)
    sticker_y: float = Field(default=0.81, ge=0, le=1)
    sticker_width: float = Field(default=0.58, ge=0.08, le=0.9)
    sticker_height: float = Field(default=0.1, ge=0.04, le=0.3)
    sticker_rotation: float = Field(default=0, ge=-180, le=180)
    sticker_font_size: int = Field(default=14, ge=14, le=32)
    sticker_font_family: StoryFontFamily = "Inter"
    sticker_italic: bool = False
    sticker_text_color: str = Field(default=STORY_DEFAULT_TEXT_COLOR, max_length=32)
    sticker_background_color: str = Field(
        default=STORY_DEFAULT_BACKGROUND_COLOR,
        max_length=32,
    )

    @field_validator("sticker_text_color")
    @classmethod
    def validate_text_color(cls, value: str) -> str:
        if value != STORY_DEFAULT_TEXT_COLOR and value not in STORY_COLORS:
            raise ValueError("A cor do texto não pertence à paleta permitida.")
        return value

    @field_validator("sticker_background_color")
    @classmethod
    def validate_background_color(cls, value: str) -> str:
        if value != STORY_DEFAULT_BACKGROUND_COLOR and value not in STORY_COLORS:
            raise ValueError("A cor de fundo não pertence à paleta permitida.")
        return value

    @model_validator(mode="after")
    def require_sticker_inside_story(self) -> "CookieStoryStickerStyle":
        if not self.sticker_width / 2 <= self.sticker_x <= 1 - self.sticker_width / 2:
            raise ValueError("A posição horizontal precisa manter o adesivo dentro do Story.")
        if not self.sticker_height / 2 <= self.sticker_y <= 1 - self.sticker_height / 2:
            raise ValueError("A posição vertical precisa manter o adesivo dentro do Story.")
        return self


class CookieStoryPresetInput(CookieStoryStickerStyle):
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


class CookieStoryPresetOut(CookieStoryStickerStyle):
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


class CookieStoryDeliveryOut(CookieStoryStickerStyle):
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
