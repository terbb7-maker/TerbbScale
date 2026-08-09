import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str | None
    full_name: str | None
    avatar_url: str | None
    status: str
    is_platform_owner: bool
    timezone: str
    locale: str
    approved_at: datetime | None
    created_at: datetime
    permissions: list[str] = Field(default_factory=list)


class BootstrapResponse(BaseModel):
    user: UserProfileOut
    created: bool


class WebSocketTicketOut(BaseModel):
    ticket: str
    expires_in: int
