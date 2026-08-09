from fastapi import APIRouter, Query
from sqlalchemy import select

from app.models.operations import AuditLog, CampaignLog
from app.modules.auth.dependencies import ActiveUserDep, SessionDep
from app.modules.logs.schemas import AuditLogOut, CampaignLogOut

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/publications", response_model=list[CampaignLogOut])
async def publication_logs(
    user: ActiveUserDep,
    session: SessionDep,
    log_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[CampaignLog]:
    query = (
        select(CampaignLog)
        .where(CampaignLog.owner_id == user.id)
        .order_by(CampaignLog.occurred_at.desc(), CampaignLog.id.desc())
        .limit(limit)
    )
    if log_status:
        query = query.where(CampaignLog.status == log_status)
    return list((await session.scalars(query)).all())


@router.get("/audit", response_model=list[AuditLogOut])
async def audit_logs(
    user: ActiveUserDep,
    session: SessionDep,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AuditLog]:
    query = (
        select(AuditLog)
        .where(AuditLog.owner_id == user.id)
        .order_by(AuditLog.occurred_at.desc(), AuditLog.id.desc())
        .limit(limit)
    )
    return list((await session.scalars(query)).all())
