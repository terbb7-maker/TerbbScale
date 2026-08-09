import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProxyInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    protocol: str = Field(pattern=r"^(http|https|socks5)$")
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535)
    username: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, max_length=2048)
    country: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=4000)
    is_active: bool = True

    @field_validator("host")
    @classmethod
    def host_has_no_scheme_or_path(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or "://" in normalized or "/" in normalized or "@" in normalized:
            raise ValueError("Host inválido. Informe apenas IP ou domínio.")
        return normalized

    @field_validator("username", "country", "notes")
    @classmethod
    def trim_optional(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None

    @model_validator(mode="after")
    def password_requires_username(self) -> "ProxyInput":
        if self.password and not self.username:
            raise ValueError("Informe o usuário quando o proxy exigir senha.")
        return self


class ProxyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    protocol: str | None = Field(default=None, pattern=r"^(http|https|socks5)$")
    host: str | None = Field(default=None, min_length=1, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, max_length=2048)
    country: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=4000)
    is_active: bool | None = None

    @field_validator("host")
    @classmethod
    def update_host_has_no_scheme_or_path(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return ProxyInput.model_validate(
            {"name": "x", "protocol": "http", "host": value, "port": 1}
        ).host


class ProxyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    protocol: str
    host: str
    port: int
    username: str | None
    password_configured: bool
    country: str | None
    notes: str | None
    is_active: bool
    status: str
    last_error: str | None
    last_check: datetime | None
    latency_ms: int | None
    public_ip: str | None
    cooldown_until: datetime | None
    consecutive_failures: int
    accounts_using: int = 0
    created_at: datetime
    updated_at: datetime


class ProxyTestOut(BaseModel):
    proxy_id: uuid.UUID
    status: str
    public_ip: str | None
    latency_ms: int | None
    checked_at: datetime
    error: str | None


class ProxyTestAllOut(BaseModel):
    tested: int
    online: int
    offline: int
    results: list[ProxyTestOut]


class ProxyImportInput(BaseModel):
    """One authenticated proxy per line: host:port:username:password."""

    entries: str = Field(min_length=1, max_length=200_000)
    protocol: str = Field(default="http", pattern=r"^(http|https|socks5)$")
    country: str | None = Field(default=None, max_length=80)
    name_prefix: str = Field(default="Proxy", min_length=1, max_length=80)
    is_active: bool = True

    @field_validator("entries")
    @classmethod
    def entries_have_at_most_500_non_empty_lines(cls, value: str) -> str:
        if len([line for line in value.splitlines() if line.strip()]) > 500:
            raise ValueError("Importe no máximo 500 proxies por vez.")
        return value

    @field_validator("country", "name_prefix")
    @classmethod
    def trim_import_optional(cls, value: str | None) -> str | None:
        return value.strip() if value and value.strip() else None


class ProxyImportError(BaseModel):
    line: int
    error: str


class ProxyImportOut(BaseModel):
    created: int
    rejected: int
    proxies: list[ProxyOut]
    errors: list[ProxyImportError]


class ProxyBulkRemoveInput(BaseModel):
    proxy_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)


class ProxyBulkRemoveOut(BaseModel):
    removed: int


class AccountProxyInput(BaseModel):
    proxy_id: uuid.UUID | None


class BulkAccountProxyInput(BaseModel):
    account_ids: list[uuid.UUID] = Field(min_length=1, max_length=5000)
    proxy_id: uuid.UUID | None
