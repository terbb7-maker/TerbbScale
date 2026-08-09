import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str | None
    full_name: str | None
    status: str
    is_platform_owner: bool
    timezone: str
    approved_at: datetime | None
    suspended_at: datetime | None
    last_seen_at: datetime | None
    created_at: datetime
    roles: list[str] = Field(default_factory=list)
    connected_accounts: int = 0
    campaigns_count: int = 0


class DecisionInput(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class AdminUserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=160)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)


class AdminUserAdminUpdate(BaseModel):
    is_admin: bool


class AdminStatsOut(BaseModel):
    users: int
    pending_users: int
    connected_accounts: int
    campaigns: int
    publications: int
    failed_publications: int


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    price_monthly: Decimal
    limits: dict[str, object]
    active: bool


class PlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=96)
    description: str | None = Field(default=None, max_length=1000)
    price_monthly: Decimal | None = Field(default=None, ge=0)
    limits: dict[str, object] | None = None
    active: bool | None = None


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_id: uuid.UUID | None
    action: str
    target_type: str
    target_id: str | None
    outcome: str
    occurred_at: datetime
