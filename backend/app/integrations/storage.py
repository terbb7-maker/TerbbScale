import asyncio
from pathlib import Path
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.core.errors import AppError


class StorageClient:
    def __init__(self) -> None:
        if not settings.SUPABASE_SECRET_KEY:
            raise AppError(
                "storage_not_configured",
                "A chave secreta do Storage não está configurada.",
                status_code=503,
            )
        self.base = f"{str(settings.SUPABASE_URL).rstrip('/')}/storage/v1"
        self.headers = {
            "apikey": settings.SUPABASE_SECRET_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SECRET_KEY}",
        }

    async def signed_url(self, bucket: str, key: str, expires_in: int = 3600) -> str:
        path = f"{quote(bucket, safe='')}/{quote(key, safe='/')}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{self.base}/object/sign/{path}",
                headers=self.headers,
                json={"expiresIn": expires_in},
            )
        if not response.is_success:
            raise AppError("storage_error", "Não foi possível assinar a mídia.", status_code=502)
        signed = response.json()["signedURL"]
        return f"{str(settings.SUPABASE_URL).rstrip('/')}/storage/v1{signed}"

    async def signed_urls(
        self, bucket: str, keys: list[str], expires_in: int = 3600
    ) -> list[str]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            async def sign(key: str) -> str:
                path = f"{quote(bucket, safe='')}/{quote(key, safe='/')}"
                response = await client.post(
                    f"{self.base}/object/sign/{path}",
                    headers=self.headers,
                    json={"expiresIn": expires_in},
                )
                if not response.is_success:
                    raise AppError(
                        "storage_error", "Não foi possível assinar a mídia.", status_code=502
                    )
                signed = response.json()["signedURL"]
                return f"{str(settings.SUPABASE_URL).rstrip('/')}/storage/v1{signed}"

            return list(await asyncio.gather(*(sign(key) for key in keys)))

    async def download_to(self, bucket: str, key: str, destination: Path) -> None:
        path = f"{quote(bucket, safe='')}/{quote(key, safe='/')}"
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "GET",
                f"{self.base}/object/authenticated/{path}",
                headers=self.headers,
            ) as response:
                if not response.is_success:
                    raise AppError(
                        "storage_error", "Não foi possível baixar a mídia.", status_code=502
                    )
                with destination.open("wb") as output:
                    async for chunk in response.aiter_bytes(1024 * 1024):
                        output.write(chunk)

    async def upload(self, bucket: str, key: str, data: bytes, content_type: str) -> None:
        path = f"{quote(bucket, safe='')}/{quote(key, safe='/')}"
        headers = {
            **self.headers,
            "content-type": content_type,
            "x-upsert": "true",
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base}/object/{path}",
                headers=headers,
                content=data,
            )
        if not response.is_success:
            raise AppError("storage_error", "Não foi possível salvar a variante.", status_code=502)

    async def remove(self, bucket: str, keys: list[str]) -> None:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                "DELETE",
                f"{self.base}/object/{quote(bucket, safe='')}",
                headers=self.headers,
                json={"prefixes": keys},
            )
        if not response.is_success:
            raise AppError("storage_error", "Não foi possível remover a mídia.", status_code=502)
