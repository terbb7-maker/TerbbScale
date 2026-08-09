import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    instagram_user_id: str
    display_name: str | None
    username: str
    profile_picture_url: str | None
    account_type: str | None
    status: str
    health_status: str
    health_confidence: str
    health_source: str | None
    health_checked_at: datetime | None
    health_last_success_at: datetime | None
    health_next_check_at: datetime
    health_consecutive_failures: int
    health_error_code: str | None
    health_error_subcode: str | None
    health_message: str | None
    health_action_required: str | None
    granted_scopes: list[str]
    token_expires_at: datetime | None
    published_count: int
    last_published_at: datetime | None
    connected_at: datetime
    proxy_id: uuid.UUID | None = None
    proxy_name: str | None = None
    proxy_status: str | None = None
    proxy_pool_size: int = 0
    proxy_rotation_mode: str = "fixed"
    proxy_rotation_every: int = 1
    proxy_rotation_counter: int = 0
    proxy_rotation_current_proxy_id: uuid.UUID | None = None


class AccountProxyPoolItem(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    is_active: bool
    priority: int
    last_selected_at: datetime | None
    cooldown_until: datetime | None


class AccountProxyPoolOut(BaseModel):
    account_id: uuid.UUID
    rotation_mode: str
    rotate_every: int
    counter: int
    current_proxy_id: uuid.UUID | None
    proxies: list[AccountProxyPoolItem]


class AccountProxyPoolInput(BaseModel):
    proxy_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    rotation_mode: str = Field(pattern=r"^(fixed|per_post|every_n_posts)$")
    rotate_every: int = Field(default=1, ge=1, le=1000)

    @model_validator(mode="after")
    def validate_rotation_interval(self) -> "AccountProxyPoolInput":
        if self.rotation_mode != "every_n_posts" and self.rotate_every != 1:
            raise ValueError("rotate_every só pode ser configurado em every_n_posts")
        if len(set(self.proxy_ids)) != len(self.proxy_ids):
            raise ValueError("Uma proxy não pode ser repetida no mesmo pool")
        return self


class ConnectResponse(BaseModel):
    authorization_url: HttpUrl
    expires_in: int


class OAuthCallbackInput(BaseModel):
    code: str
    state: str


class AccountHealthCheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    details: dict[str, object]
    checked_at: datetime


class AccountBulkRemoveInput(BaseModel):
    account_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def account_ids_are_unique(self) -> "AccountBulkRemoveInput":
        if len(set(self.account_ids)) != len(self.account_ids):
            raise ValueError("Uma conta não pode ser repetida na seleção.")
        return self


class AccountBulkRemoveOut(BaseModel):
    removed: int
