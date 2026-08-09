import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import jwt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    id: str
    email: str | None
    session_id: str | None
    claims: dict[str, Any]


class SecretBox:
    def __init__(self, encoded_key: str) -> None:
        raw = base64.urlsafe_b64decode(encoded_key + "=" * (-len(encoded_key) % 4))
        if len(raw) != 32:
            raise ValueError("APP_ENCRYPTION_KEY must decode to exactly 32 bytes")
        self._cipher = AESGCM(raw)

    def encrypt(self, plaintext: str, *, context: str) -> str:
        nonce = secrets.token_bytes(12)
        ciphertext = self._cipher.encrypt(nonce, plaintext.encode(), context.encode())
        return base64.urlsafe_b64encode(nonce + ciphertext).decode()

    def decrypt(self, encoded: str, *, context: str) -> str:
        payload = base64.urlsafe_b64decode(encoded)
        return self._cipher.decrypt(payload[:12], payload[12:], context.encode()).decode()


secret_box = SecretBox(settings.APP_ENCRYPTION_KEY)


def token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_oauth_state() -> str:
    return secrets.token_urlsafe(48)


def sign_internal_payload(payload: dict[str, Any], expires_in: timedelta) -> str:
    now = datetime.now(UTC)
    body = {**payload, "iat": int(now.timestamp()), "exp": int((now + expires_in).timestamp())}
    encoded = base64.urlsafe_b64encode(json.dumps(body, separators=(",", ":")).encode()).decode()
    signature = hmac.new(settings.INTERNAL_API_KEY.encode(), encoded.encode(), hashlib.sha256)
    return f"{encoded}.{signature.hexdigest()}"


def verify_internal_payload(value: str) -> dict[str, Any]:
    encoded, supplied = value.rsplit(".", 1)
    expected = hmac.new(settings.INTERNAL_API_KEY.encode(), encoded.encode(), hashlib.sha256)
    if not hmac.compare_digest(expected.hexdigest(), supplied):
        raise ValueError("Invalid signature")
    payload = json.loads(base64.urlsafe_b64decode(encoded))
    if payload["exp"] < int(datetime.now(UTC).timestamp()):
        raise ValueError("Expired payload")
    return payload


async def verify_supabase_token(token: str) -> AuthenticatedUser:
    headers = {
        "apikey": settings.SUPABASE_PUBLISHABLE_KEY,
        "Authorization": f"Bearer {token}",
    }
    async with httpx.AsyncClient(timeout=8.0) as client:
        response = await client.get(f"{settings.SUPABASE_URL}/auth/v1/user", headers=headers)
    if response.status_code != 200:
        raise jwt.InvalidTokenError("Supabase rejected the access token")
    data = response.json()
    claims = jwt.decode(token, options={"verify_signature": False, "verify_exp": True})
    return AuthenticatedUser(
        id=data["id"],
        email=data.get("email"),
        session_id=claims.get("session_id"),
        claims=claims,
    )
