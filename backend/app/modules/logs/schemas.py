import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CampaignLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    campaign_id: uuid.UUID | None
    job_id: uuid.UUID | None
    account_id: uuid.UUID | None
    media_id: uuid.UUID | None
    event_type: str
    status: str
    message: str | None
    details: dict[str, object]
    occurred_at: datetime
    duration_ms: int | None


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_id: uuid.UUID | None
    action: str
    target_type: str
    target_id: str | None
    outcome: str
    request_id: str | None
    occurred_at: datetime
