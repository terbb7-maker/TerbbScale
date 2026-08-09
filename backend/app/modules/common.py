import base64
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class Cursor:
    created_at: datetime
    id: uuid.UUID

    def encode(self) -> str:
        payload = json.dumps(
            {"created_at": self.created_at.isoformat(), "id": str(self.id)},
            separators=(",", ":"),
        )
        return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")

    @classmethod
    def decode(cls, value: str) -> "Cursor":
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        payload: dict[str, Any] = json.loads(raw)
        return cls(
            created_at=datetime.fromisoformat(payload["created_at"]),
            id=uuid.UUID(payload["id"]),
        )


def safe_external_payload(value: object, *, max_chars: int = 8000) -> dict[str, object]:
    blocked = {"access_token", "refresh_token", "app_secret", "authorization", "password"}

    def scrub(item: object) -> object:
        if isinstance(item, dict):
            return {
                str(key): ("[REDACTED]" if str(key).lower() in blocked else scrub(val))
                for key, val in item.items()
            }
        if isinstance(item, list):
            return [scrub(part) for part in item[:100]]
        if isinstance(item, str) and len(item) > 2000:
            return item[:2000] + "…"
        return item

    scrubbed = scrub(value)
    encoded = json.dumps(scrubbed, default=str)
    if len(encoded) > max_chars:
        return {"truncated": True, "preview": encoded[:max_chars]}
    return scrubbed if isinstance(scrubbed, dict) else {"value": scrubbed}
