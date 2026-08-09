import uuid
from datetime import timedelta
from pathlib import PurePosixPath

from fastapi import APIRouter, Query, status
from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.errors import AppError
from app.integrations.storage import StorageClient
from app.models.media import Media, MediaTag, MediaTagLink, UploadSession
from app.modules.audit import record_audit
from app.modules.auth.dependencies import ActiveUserDep, SessionDep
from app.modules.common import utcnow
from app.modules.media.schemas import (
    MediaBulkRemoveInput,
    MediaBulkRemoveOut,
    MediaOut,
    MediaPreviewBatchInput,
    MediaPreviewBatchOut,
    MediaPreviewItem,
    MediaPreviewOut,
    MediaTagCreate,
    MediaTagOut,
    MediaUpdate,
    UploadComplete,
    UploadCreate,
    UploadOut,
)

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/tags", response_model=list[MediaTagOut])
async def list_tags(user: ActiveUserDep, session: SessionDep) -> list[MediaTag]:
    return list(
        (
            await session.scalars(
                select(MediaTag).where(MediaTag.owner_id == user.id).order_by(MediaTag.name.asc())
            )
        ).all()
    )


@router.post("/tags", response_model=MediaTagOut, status_code=status.HTTP_201_CREATED)
async def create_tag(
    payload: MediaTagCreate,
    user: ActiveUserDep,
    session: SessionDep,
) -> MediaTag:
    tag = MediaTag(
        owner_id=user.id,
        name=payload.name.strip(),
        color=payload.color,
    )
    session.add(tag)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AppError("tag_exists", "Essa tag já existe.", status_code=409) from exc
    await session.refresh(tag)
    return tag


@router.delete("/tags/{tag_id}", status_code=204)
async def delete_tag(
    tag_id: uuid.UUID,
    user: ActiveUserDep,
    session: SessionDep,
) -> None:
    result = await session.execute(
        delete(MediaTag).where(MediaTag.id == tag_id, MediaTag.owner_id == user.id)
    )
    if result.rowcount == 0:
        raise AppError("tag_not_found", "Tag não encontrada.", status_code=404)
    await session.commit()


@router.get("", response_model=list[MediaOut])
async def list_media(
    user: ActiveUserDep,
    session: SessionDep,
    kind: str | None = None,
    media_status: str | None = Query(default=None, alias="status"),
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Media]:
    query = (
        select(Media)
        .where(Media.owner_id == user.id, Media.deleted_at.is_(None))
        .order_by(Media.created_at.desc(), Media.id.desc())
        .limit(limit)
    )
    if kind:
        query = query.where(Media.media_kind == kind)
    if media_status:
        query = query.where(Media.status == media_status)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(or_(Media.display_name.ilike(term), Media.original_name.ilike(term)))
    return list((await session.scalars(query)).all())


@router.post("/uploads", response_model=UploadOut, status_code=status.HTTP_201_CREATED)
async def create_upload(
    payload: UploadCreate,
    user: ActiveUserDep,
    session: SessionDep,
) -> UploadOut:
    now = utcnow()
    upload_id = uuid.uuid4()
    safe_suffix = PurePosixPath(payload.original_name).suffix.lower()[:12]
    storage_key = f"{user.id}/media/{upload_id}/original{safe_suffix}"
    upload = UploadSession(
        id=upload_id,
        owner_id=user.id,
        storage_key=storage_key,
        original_name=PurePosixPath(payload.original_name).name,
        mime_type=payload.mime_type,
        expected_size_bytes=payload.size_bytes,
        status="created",
        expires_at=now + timedelta(hours=1),
    )
    session.add(upload)
    await session.commit()
    return UploadOut(
        id=upload.id,
        bucket=settings.SUPABASE_STORAGE_BUCKET,
        storage_key=storage_key,
        expires_at=upload.expires_at,
    )


@router.post("/uploads/{upload_id}/complete", response_model=MediaOut)
async def complete_upload(
    upload_id: uuid.UUID,
    payload: UploadComplete,
    user: ActiveUserDep,
    session: SessionDep,
) -> Media:
    upload = await session.scalar(
        select(UploadSession).where(
            UploadSession.id == upload_id,
            UploadSession.owner_id == user.id,
            UploadSession.status == "created",
            UploadSession.expires_at > utcnow(),
        )
    )
    if upload is None or payload.storage_key != upload.storage_key:
        raise AppError("invalid_upload", "Upload inválido ou expirado.", status_code=409)
    now = utcnow()
    media = Media(
        owner_id=user.id,
        original_name=upload.original_name,
        display_name=upload.original_name,
        storage_bucket=settings.SUPABASE_STORAGE_BUCKET,
        storage_key=upload.storage_key,
        mime_type=upload.mime_type,
        media_kind=upload.mime_type.split("/", 1)[0],
        size_bytes=upload.expected_size_bytes,
        status="processing",
        compatibility={},
        uploaded_at=now,
    )
    upload.status = "completed"
    upload.completed_at = now
    session.add(media)
    await session.commit()
    await session.refresh(media)
    from app.workers.tasks import process_media_task

    process_media_task.apply_async(args=[str(media.id)], queue="media")
    return media


@router.post("/previews", response_model=MediaPreviewBatchOut)
async def media_previews(
    payload: MediaPreviewBatchInput,
    user: ActiveUserDep,
    session: SessionDep,
) -> MediaPreviewBatchOut:
    media_ids = list(dict.fromkeys(payload.media_ids))
    items = list(
        (
            await session.scalars(
                select(Media)
                .where(
                    Media.id.in_(media_ids),
                    Media.owner_id == user.id,
                    Media.deleted_at.is_(None),
                )
                .order_by(Media.created_at.desc())
            )
        ).all()
    )
    if len(items) != len(media_ids):
        raise AppError(
            "media_not_found",
            "Uma ou mais mídias não foram encontradas.",
            status_code=404,
        )
    expires_in = 900
    signable = [
        item for item in items if item.thumbnail_key is not None or item.media_kind == "image"
    ]
    urls = await StorageClient().signed_urls(
        settings.SUPABASE_STORAGE_BUCKET,
        [item.thumbnail_key or item.storage_key for item in signable],
        expires_in,
    )
    urls_by_media = {
        item.id: url for item, url in zip(signable, urls, strict=True)
    }
    return MediaPreviewBatchOut(
        previews=[
            MediaPreviewItem(media_id=item.id, url=urls_by_media.get(item.id))
            for item in items
        ],
        expires_at=utcnow() + timedelta(seconds=expires_in),
    )


@router.post("/bulk-remove", response_model=MediaBulkRemoveOut)
async def bulk_remove_media(
    payload: MediaBulkRemoveInput,
    user: ActiveUserDep,
    session: SessionDep,
) -> MediaBulkRemoveOut:
    media_ids = list(dict.fromkeys(payload.media_ids))
    owned_ids = set(
        (
            await session.scalars(
                select(Media.id).where(
                    Media.id.in_(media_ids),
                    Media.owner_id == user.id,
                    Media.deleted_at.is_(None),
                )
            )
        ).all()
    )
    if owned_ids != set(media_ids):
        raise AppError(
            "media_not_found",
            "Uma ou mais mídias não foram encontradas.",
            status_code=404,
        )
    remove_at = utcnow() + timedelta(days=settings.MEDIA_RETENTION_DAYS)
    await session.execute(
        update(Media)
        .where(Media.id.in_(media_ids), Media.owner_id == user.id)
        .values(status="deleting", deleted_at=remove_at)
    )
    await record_audit(
        session,
        action="media_bulk_removed",
        target_type="media",
        actor_id=user.id,
        owner_id=user.id,
        after={"removed": len(media_ids), "media_ids": [str(item) for item in media_ids]},
    )
    await session.commit()
    return MediaBulkRemoveOut(removed=len(media_ids))


@router.get("/{media_id}/preview", response_model=MediaPreviewOut)
async def media_preview(
    media_id: uuid.UUID,
    user: ActiveUserDep,
    session: SessionDep,
) -> MediaPreviewOut:
    media = await session.scalar(
        select(Media).where(
            Media.id == media_id,
            Media.owner_id == user.id,
            Media.deleted_at.is_(None),
        )
    )
    if media is None:
        raise AppError("media_not_found", "Mídia não encontrada.", status_code=404)
    expires_in = 900
    url = await StorageClient().signed_url(
        media.storage_bucket,
        media.thumbnail_key or media.storage_key,
        expires_in,
    )
    return MediaPreviewOut(
        url=url,
        expires_at=utcnow() + timedelta(seconds=expires_in),
    )


@router.patch("/{media_id}", response_model=MediaOut)
async def update_media(
    media_id: uuid.UUID,
    payload: MediaUpdate,
    user: ActiveUserDep,
    session: SessionDep,
) -> Media:
    media = await session.scalar(
        select(Media).where(
            Media.id == media_id,
            Media.owner_id == user.id,
            Media.deleted_at.is_(None),
        )
    )
    if media is None:
        raise AppError("media_not_found", "Mídia não encontrada.", status_code=404)
    if payload.display_name is not None:
        media.display_name = payload.display_name
    if payload.tag_ids is not None:
        requested_tags = set(payload.tag_ids)
        owned_tags = set(
            (
                await session.scalars(
                    select(MediaTag.id).where(
                        MediaTag.owner_id == user.id,
                        MediaTag.id.in_(requested_tags),
                    )
                )
            ).all()
        )
        if requested_tags != owned_tags:
            raise AppError(
                "invalid_media_tags",
                "Uma ou mais tags não pertencem ao usuário.",
                status_code=422,
            )
        links = list(
            (
                await session.scalars(select(MediaTagLink).where(MediaTagLink.media_id == media.id))
            ).all()
        )
        for link in links:
            await session.delete(link)
        for tag_id in set(payload.tag_ids):
            session.add(MediaTagLink(media_id=media.id, tag_id=tag_id))
    await session.commit()
    return media


@router.delete("/{media_id}", status_code=204)
async def delete_media(
    media_id: uuid.UUID,
    user: ActiveUserDep,
    session: SessionDep,
) -> None:
    media = await session.scalar(
        select(Media).where(
            Media.id == media_id,
            Media.owner_id == user.id,
            Media.deleted_at.is_(None),
        )
    )
    if media is None:
        raise AppError("media_not_found", "Mídia não encontrada.", status_code=404)
    media.status = "deleting"
    media.deleted_at = utcnow() + timedelta(days=settings.MEDIA_RETENTION_DAYS)
    await session.commit()
