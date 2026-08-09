import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operations import AuditLog
from app.modules.common import utcnow


async def record_audit(
    session: AsyncSession,
    *,
    action: str,
    target_type: str,
    actor_id: uuid.UUID | None,
    owner_id: uuid.UUID | None,
    target_id: str | None = None,
    outcome: str = "success",
    request_id: str | None = None,
    before: dict[str, object] | None = None,
    after: dict[str, object] | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    session.add(
        AuditLog(
            owner_id=owner_id,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            outcome=outcome,
            request_id=request_id,
            before_json=before,
            after_json=after,
            metadata_json=metadata or {},
            occurred_at=utcnow(),
        )
    )
