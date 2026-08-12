import uuid
from datetime import timedelta
from urllib.parse import urlsplit

from fastapi import APIRouter, Response, status
from sqlalchemy import select

from app.core.config import settings
from app.core.errors import AppError
from app.integrations.storage import StorageClient
from app.models.media import CookieStoryPreset, Media
from app.modules.audit import record_audit
from app.modules.auth.dependencies import ActiveUserDep, SessionDep
from app.modules.common import utcnow
from app.modules.cookie_story.schemas import (
    CookieStoryDeliveryOut,
    CookieStoryPresetInput,
    CookieStoryPresetOut,
)

router = APIRouter(prefix="/cookie-story", tags=["cookie-story"])

DELIVERY_TTL_SECONDS = 300
MAX_IMAGE_BYTES = 25 * 1024 * 1024
MAX_VIDEO_BYTES = 100 * 1024 * 1024
MAX_VIDEO_DURATION_MS = 60_000
STORY_RATIO = 9 / 16
STORY_RATIO_TOLERANCE = 0.04


def _require_feature() -> None:
    if not settings.COOKIE_STORY_ENABLED:
        raise AppError(
            "cookie_story_disabled",
            "A publicação local de Story está temporariamente desativada.",
            status_code=503,
        )


async def _preset_and_media(
    owner_id: uuid.UUID,
    session: SessionDep,
) -> tuple[CookieStoryPreset, Media] | None:
    row = (
        await session.execute(
            select(CookieStoryPreset, Media)
            .join(Media, Media.id == CookieStoryPreset.media_id)
            .where(
                CookieStoryPreset.owner_id == owner_id,
                Media.owner_id == owner_id,
                Media.deleted_at.is_(None),
            )
        )
    ).one_or_none()
    return (row[0], row[1]) if row else None


def _validate_story_media(media: Media) -> None:
    if media.status != "ready" or media.compatibility.get("story") is not True:
        raise AppError(
            "story_media_not_ready",
            "A mídia precisa estar pronta e compatível com Stories.",
            status_code=409,
        )
    if not media.width or not media.height:
        raise AppError(
            "story_media_metadata_missing",
            "A mídia ainda não possui dimensões verificadas.",
            status_code=409,
        )
    if media.media_kind == "image":
        if media.size_bytes > MAX_IMAGE_BYTES:
            raise AppError(
                "story_image_too_large",
                "A imagem do Story deve ter no máximo 25 MB.",
                status_code=409,
            )
        return
    if media.media_kind != "video" or media.mime_type != "video/mp4":
        raise AppError(
            "story_video_format_invalid",
            "Para o conector local, use um vídeo MP4.",
            status_code=409,
        )
    ratio = media.width / media.height
    if abs(ratio - STORY_RATIO) > STORY_RATIO_TOLERANCE:
        raise AppError(
            "story_video_ratio_invalid",
            "O vídeo precisa estar no formato vertical 9:16.",
            status_code=409,
        )
    if media.size_bytes > MAX_VIDEO_BYTES:
        raise AppError(
            "story_video_too_large",
            "O vídeo do Story deve ter no máximo 100 MB.",
            status_code=409,
        )
    if not media.duration_ms or media.duration_ms > MAX_VIDEO_DURATION_MS:
        raise AppError(
            "story_video_duration_invalid",
            "O vídeo precisa ter duração verificada de até 60 segundos.",
            status_code=409,
        )


async def _serialize(
    preset: CookieStoryPreset,
    media: Media,
    *,
    include_preview: bool = False,
) -> CookieStoryPresetOut:
    preview_url = None
    if include_preview and (media.thumbnail_key or media.media_kind == "image"):
        preview_url = await StorageClient().signed_url(
            media.storage_bucket,
            media.thumbnail_key or media.storage_key,
            DELIVERY_TTL_SECONDS,
        )
    return CookieStoryPresetOut(
        id=preset.id,
        media_id=media.id,
        media_name=media.display_name,
        media_kind=media.media_kind,
        mime_type=media.mime_type,
        size_bytes=media.size_bytes,
        width=media.width,
        height=media.height,
        duration_ms=media.duration_ms,
        preview_url=preview_url,
        link_url=preset.link_url,
        link_title=preset.link_title,
        updated_at=preset.updated_at,
    )


@router.get("/preset", response_model=CookieStoryPresetOut | None)
async def read_preset(user: ActiveUserDep, session: SessionDep) -> CookieStoryPresetOut | None:
    _require_feature()
    row = await _preset_and_media(user.id, session)
    return await _serialize(*row, include_preview=True) if row else None


@router.put("/preset", response_model=CookieStoryPresetOut)
async def save_preset(
    payload: CookieStoryPresetInput,
    user: ActiveUserDep,
    session: SessionDep,
) -> CookieStoryPresetOut:
    _require_feature()
    media = await session.scalar(
        select(Media).where(
            Media.id == payload.media_id,
            Media.owner_id == user.id,
            Media.deleted_at.is_(None),
        )
    )
    if media is None:
        raise AppError("media_not_found", "Mídia não encontrada.", status_code=404)
    _validate_story_media(media)

    preset = await session.scalar(
        select(CookieStoryPreset).where(CookieStoryPreset.owner_id == user.id)
    )
    before = None
    if preset is None:
        preset = CookieStoryPreset(owner_id=user.id, media_id=media.id, link_url="")
        session.add(preset)
    else:
        before = {
            "media_id": str(preset.media_id),
            "link_host": urlsplit(preset.link_url).hostname,
        }
    preset.media_id = media.id
    preset.link_url = str(payload.link_url)
    preset.link_title = payload.link_title
    await session.flush()
    await record_audit(
        session,
        action="cookie_story_preset_saved",
        target_type="cookie_story_preset",
        actor_id=user.id,
        owner_id=user.id,
        target_id=str(preset.id),
        before=before,
        after={
            "media_id": str(media.id),
            "link_host": payload.link_url.host,
        },
    )
    await session.commit()
    await session.refresh(preset)
    return await _serialize(preset, media, include_preview=True)


@router.delete("/preset", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preset(user: ActiveUserDep, session: SessionDep) -> Response:
    _require_feature()
    preset = await session.scalar(
        select(CookieStoryPreset).where(CookieStoryPreset.owner_id == user.id)
    )
    if preset is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    preset_id = preset.id
    await session.delete(preset)
    await record_audit(
        session,
        action="cookie_story_preset_removed",
        target_type="cookie_story_preset",
        actor_id=user.id,
        owner_id=user.id,
        target_id=str(preset_id),
    )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/delivery", response_model=CookieStoryDeliveryOut)
async def create_delivery(
    user: ActiveUserDep,
    session: SessionDep,
) -> CookieStoryDeliveryOut:
    _require_feature()
    row = await _preset_and_media(user.id, session)
    if row is None:
        raise AppError(
            "cookie_story_preset_missing",
            "Configure o Story antes de publicar.",
            status_code=409,
        )
    preset, media = row
    _validate_story_media(media)
    expires_at = utcnow() + timedelta(seconds=DELIVERY_TTL_SECONDS)
    media_url = await StorageClient().signed_url(
        media.storage_bucket,
        media.storage_key,
        DELIVERY_TTL_SECONDS,
    )
    return CookieStoryDeliveryOut(
        preset_id=preset.id,
        preset_version=preset.updated_at.isoformat(),
        media_id=media.id,
        media_url=media_url,
        media_name=media.display_name,
        media_kind=media.media_kind,
        mime_type=media.mime_type,
        size_bytes=media.size_bytes,
        width=media.width,
        height=media.height,
        duration_ms=media.duration_ms,
        link_url=preset.link_url,
        link_title=preset.link_title,
        expires_at=expires_at,
    )
