import uuid

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, update

from app.core.errors import AppError
from app.models.operations import Notification
from app.modules.auth.dependencies import ActiveUserDep, SessionDep
from app.modules.common import utcnow

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    title: str
    message: str
    severity: str
    data: dict[str, object]
    read_at: object | None
    created_at: object


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    user: ActiveUserDep,
    session: SessionDep,
) -> list[Notification]:
    query = (
        select(Notification)
        .where(Notification.owner_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(100)
    )
    return list((await session.scalars(query)).all())


@router.post("/read-all", status_code=204)
async def mark_all_read(user: ActiveUserDep, session: SessionDep) -> None:
    await session.execute(
        update(Notification)
        .where(Notification.owner_id == user.id, Notification.read_at.is_(None))
        .values(read_at=utcnow())
    )
    await session.commit()


@router.post("/{notification_id}/read", status_code=204)
async def mark_read(
    notification_id: uuid.UUID,
    user: ActiveUserDep,
    session: SessionDep,
) -> None:
    notification = await session.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.owner_id == user.id,
        )
    )
    if notification is None:
        raise AppError("notification_not_found", "Notificação não encontrada.", status_code=404)
    notification.read_at = utcnow()
    await session.commit()
