import asyncio
import hashlib
import json
import tempfile
import uuid
from pathlib import Path

from sqlalchemy import select

from app.core.database import SessionFactory
from app.integrations.storage import StorageClient
from app.models.media import Media, MediaVariant


async def _probe(path: Path) -> dict[str, object]:
    process = await asyncio.create_subprocess_exec(
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=codec_type,width,height,codec_name",
        "-of",
        "json",
        str(path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode:
        raise ValueError(stderr.decode(errors="replace")[:1000])
    return json.loads(stdout)


async def _thumbnail(source: Path, destination: Path) -> None:
    process = await asyncio.create_subprocess_exec(
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-vf",
        "thumbnail,scale='min(960,iw)':-2",
        "-frames:v",
        "1",
        str(destination),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.PIPE,
    )
    _, stderr = await process.communicate()
    if process.returncode:
        raise ValueError(stderr.decode(errors="replace")[-1000:])


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


async def process_media(media_id: uuid.UUID) -> None:
    async with SessionFactory() as session:
        media = await session.scalar(select(Media).where(Media.id == media_id))
        if media is None or media.status not in {"processing", "invalid"}:
            return
        storage = StorageClient()
        try:
            with tempfile.TemporaryDirectory(prefix="postx-media-") as temp_dir:
                source = Path(temp_dir) / "source"
                thumb = Path(temp_dir) / "thumbnail.jpg"
                await storage.download_to(media.storage_bucket, media.storage_key, source)
                probe = await _probe(source)
                streams = probe.get("streams", [])
                visual = next(
                    (stream for stream in streams if stream.get("codec_type") == "video"),
                    next((stream for stream in streams if stream.get("codec_type") == "image"), {}),
                )
                await _thumbnail(source, thumb)
                thumbnail_key = f"{media.owner_id}/media/{media.id}/thumbnail.jpg"
                await storage.upload(
                    media.storage_bucket,
                    thumbnail_key,
                    thumb.read_bytes(),
                    "image/jpeg",
                )
                duration = float(probe.get("format", {}).get("duration") or 0)
                media.content_hash = _hash(source)
                media.width = visual.get("width")
                media.height = visual.get("height")
                media.duration_ms = round(duration * 1000) if duration else None
                media.thumbnail_key = thumbnail_key
                media.compatibility = {
                    "feed": media.media_kind in {"image", "video"},
                    "reel": media.media_kind == "video",
                    "story": media.media_kind in {"image", "video"},
                    "codec": visual.get("codec_name"),
                }
                media.status = "ready"
                media.failure_reason = None
                session.add(
                    MediaVariant(
                        owner_id=media.owner_id,
                        media_id=media.id,
                        variant_type="thumbnail",
                        storage_key=thumbnail_key,
                        mime_type="image/jpeg",
                        size_bytes=thumb.stat().st_size,
                        metadata_json={"width": media.width, "height": media.height},
                    )
                )
        except Exception as exc:
            media.status = "invalid"
            media.failure_reason = str(exc)[:1000]
        await session.commit()
