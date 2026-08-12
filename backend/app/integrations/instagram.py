from collections.abc import Collection
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.modules.common import safe_external_payload


@dataclass(frozen=True, slots=True)
class InstagramProfile:
    id: str
    username: str
    name: str | None
    profile_picture_url: str | None
    account_type: str | None


class InstagramAPIError(Exception):
    def __init__(
        self,
        error_class: str,
        message: str,
        *,
        retryable: bool,
        status_code: int | None = None,
        provider_code: int | None = None,
        provider_subcode: int | None = None,
        payload: dict[str, object] | None = None,
    ) -> None:
        self.error_class = error_class
        self.retryable = retryable
        self.status_code = status_code
        self.provider_code = provider_code
        self.provider_subcode = provider_subcode
        self.payload = payload or {}
        super().__init__(message)


class InstagramClient:
    def __init__(
        self, *, app_id: str, app_secret: str, http_client: httpx.AsyncClient | None = None
    ) -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self.http = http_client
        self.graph = str(settings.INSTAGRAM_GRAPH_BASE_URL).rstrip("/")

    def authorization_url(self, *, redirect_uri: str, scopes: list[str], state: str) -> str:
        query = urlencode(
            {
                "client_id": self.app_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": ",".join(scopes),
                "state": state,
            }
        )
        return f"{str(settings.INSTAGRAM_OAUTH_BASE_URL).rstrip('/')}/authorize?{query}"

    async def exchange_code(self, *, code: str, redirect_uri: str) -> dict[str, Any]:
        response = await self._http().post(
            "https://api.instagram.com/oauth/access_token",
            data={
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
                "code": code,
            },
        )
        return self._json_or_raise(response)

    async def exchange_long_lived_token(self, token: str) -> dict[str, Any]:
        response = await self._http().get(
            f"{self.graph}/access_token",
            params={
                "grant_type": "ig_exchange_token",
                "client_secret": self.app_secret,
                "access_token": token,
            },
        )
        return self._json_or_raise(response)

    async def refresh_token(self, token: str) -> dict[str, Any]:
        response = await self._http().get(
            f"{self.graph}/refresh_access_token",
            params={"grant_type": "ig_refresh_token", "access_token": token},
        )
        return self._json_or_raise(response)

    async def profile(self, user_id: str, token: str) -> InstagramProfile:
        response = await self._http().get(
            f"{self.graph}/{settings.INSTAGRAM_API_VERSION}/{user_id}",
            params={
                "fields": "id,user_id,username,name,profile_picture_url,account_type",
                "access_token": token,
            },
        )
        data = self._json_or_raise(response)
        return InstagramProfile(
            id=str(data.get("user_id") or data["id"]),
            username=data["username"],
            name=data.get("name"),
            profile_picture_url=data.get("profile_picture_url"),
            account_type=data.get("account_type"),
        )

    async def create_container(
        self,
        *,
        account_id: str,
        token: str,
        media_url: str,
        media_type: str,
        is_image: bool,
        caption: str | None,
        cover_url: str | None = None,
    ) -> str:
        data: dict[str, str] = {"access_token": token}
        if is_image:
            data["image_url"] = media_url
            if media_type == "STORIES":
                data["media_type"] = media_type
        else:
            data["video_url"] = media_url
            data["media_type"] = media_type
        if caption:
            data["caption"] = caption
        if cover_url:
            data["cover_url"] = cover_url
        response = await self._http().post(
            f"{self.graph}/{settings.INSTAGRAM_API_VERSION}/{account_id}/media",
            data=data,
        )
        return str(self._json_or_raise(response)["id"])

    async def container_status(self, container_id: str, token: str) -> str:
        response = await self._http().get(
            f"{self.graph}/{settings.INSTAGRAM_API_VERSION}/{container_id}",
            params={"fields": "status_code,status", "access_token": token},
        )
        return str(self._json_or_raise(response).get("status_code", "UNKNOWN"))

    async def publish(self, *, account_id: str, container_id: str, token: str) -> str:
        response = await self._http().post(
            f"{self.graph}/{settings.INSTAGRAM_API_VERSION}/{account_id}/media_publish",
            data={"creation_id": container_id, "access_token": token},
        )
        return str(self._json_or_raise(response)["id"])

    async def publishing_limit(self, account_id: str, token: str) -> dict[str, Any]:
        response = await self._http().get(
            f"{self.graph}/{settings.INSTAGRAM_API_VERSION}/{account_id}/content_publishing_limit",
            params={"fields": "quota_usage,config", "access_token": token},
        )
        return self._json_or_raise(response)

    async def media_insights(
        self,
        media_id: str,
        token: str,
        metrics: Collection[str],
    ) -> dict[str, Any]:
        response = await self._http().get(
            f"{self.graph}/{settings.INSTAGRAM_API_VERSION}/{media_id}/insights",
            params={
                "metric": ",".join(metrics),
                "access_token": token,
            },
        )
        return self._json_or_raise(response)

    @staticmethod
    def _json_or_raise(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            payload = {"message": response.text[:1000]}
        if response.is_success:
            return payload
        status = response.status_code
        error = payload.get("error", payload)
        provider_code = _optional_int(error.get("code"))
        provider_subcode = _optional_int(error.get("error_subcode"))
        error_class = "unknown_provider_error"
        retryable = False
        if status == 429:
            error_class, retryable = "rate_limited", True
        elif status >= 500:
            error_class, retryable = "temporary_provider_error", True
        elif status == 401:
            error_class = "auth_expired"
        elif status == 403:
            error_class = "permission_missing"
        elif status == 400:
            error_class = "media_invalid"
        raise InstagramAPIError(
            error_class,
            str(error.get("message", "Instagram API error")),
            retryable=retryable,
            status_code=status,
            provider_code=provider_code,
            provider_subcode=provider_subcode,
            payload=safe_external_payload(payload),
        )

    def _http(self) -> httpx.AsyncClient:
        if self.http is None:
            raise RuntimeError("InstagramClient requires an HTTP client for network operations")
        return self.http


def _optional_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
