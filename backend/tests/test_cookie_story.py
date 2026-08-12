import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.core.errors import AppError
from app.modules.cookie_story.router import _validate_story_media
from app.modules.cookie_story.schemas import CookieStoryPresetInput


def media(**changes: object) -> SimpleNamespace:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "status": "ready",
        "compatibility": {"story": True},
        "media_kind": "image",
        "mime_type": "image/jpeg",
        "size_bytes": 1_000_000,
        "width": 1080,
        "height": 1920,
        "duration_ms": None,
        "updated_at": datetime.now(UTC),
    }
    return SimpleNamespace(**(defaults | changes))


@pytest.mark.parametrize(
    "link",
    [
        "http://example.com",
        "https://user:password@example.com/path",
    ],
)
def test_cookie_story_preset_rejects_unsafe_link(link: str) -> None:
    with pytest.raises(ValidationError):
        CookieStoryPresetInput(media_id=uuid.uuid4(), link_url=link)


def test_cookie_story_preset_normalizes_link_title() -> None:
    payload = CookieStoryPresetInput(
        media_id=uuid.uuid4(),
        link_url="https://example.com/path",
        link_title="  Saiba mais  ",
    )
    assert payload.link_title == "Saiba mais"


def test_cookie_story_preset_accepts_complete_sticker_style() -> None:
    payload = CookieStoryPresetInput(
        media_id=uuid.uuid4(),
        link_url="https://example.com/path",
        sticker_x=0.35,
        sticker_y=0.42,
        sticker_width=0.4,
        sticker_height=0.08,
        sticker_rotation=-25,
        sticker_font_size=24,
        sticker_font_family="Great Vibes",
        sticker_italic=True,
        sticker_text_color="rgba(255, 192, 10, 1)",
        sticker_background_color="rgba(115, 0, 255, 1)",
    )
    assert payload.sticker_font_family == "Great Vibes"
    assert payload.sticker_rotation == -25


@pytest.mark.parametrize(
    "changes",
    [
        {"sticker_x": 0.1, "sticker_width": 0.58},
        {"sticker_y": 0.98, "sticker_height": 0.1},
        {"sticker_font_family": "Comic Sans"},
        {"sticker_text_color": "url(javascript:alert(1))"},
        {"sticker_background_color": "transparent"},
    ],
)
def test_cookie_story_preset_rejects_invalid_sticker_style(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        CookieStoryPresetInput(
            media_id=uuid.uuid4(),
            link_url="https://example.com/path",
            **changes,
        )


def test_cookie_story_accepts_ready_image() -> None:
    _validate_story_media(media())


def test_cookie_story_accepts_vertical_mp4() -> None:
    _validate_story_media(
        media(
            media_kind="video",
            mime_type="video/mp4",
            size_bytes=10_000_000,
            duration_ms=15_000,
        )
    )


@pytest.mark.parametrize(
    "changes, code",
    [
        ({"status": "processing"}, "story_media_not_ready"),
        ({"width": None}, "story_media_metadata_missing"),
        ({"size_bytes": 26 * 1024 * 1024}, "story_image_too_large"),
        (
            {
                "media_kind": "video",
                "mime_type": "video/webm",
                "duration_ms": 10_000,
            },
            "story_video_format_invalid",
        ),
        (
            {
                "media_kind": "video",
                "mime_type": "video/mp4",
                "width": 1920,
                "height": 1080,
                "duration_ms": 10_000,
            },
            "story_video_ratio_invalid",
        ),
        (
            {
                "media_kind": "video",
                "mime_type": "video/mp4",
                "duration_ms": 61_000,
            },
            "story_video_duration_invalid",
        ),
    ],
)
def test_cookie_story_rejects_incompatible_media(
    changes: dict[str, object],
    code: str,
) -> None:
    with pytest.raises(AppError) as raised:
        _validate_story_media(media(**changes))
    assert raised.value.code == code
