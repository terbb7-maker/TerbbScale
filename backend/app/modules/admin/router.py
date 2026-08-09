import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select, update

from app.core.database import database_ready
from app.core.errors import AppError
from app.core.redis import redis_ready
from app.models.campaigns import Campaign, Job
from app.models.identity import Approval, Role, User, UserRole
from app.models.instagram import Account
from app.models.operations import AuditLog, Plan, SchedulerState, UserPlan
from app.modules.admin.schemas import (
    AdminStatsOut,
    AdminUserAdminUpdate,
    AdminUserOut,
    AdminUserUpdate,
    AuditLogOut,
    DecisionInput,
    PlanOut,
    PlanUpdate,
)
from app.modules.audit import record_audit
from app.modules.auth.dependencies import SessionDep, require_permission, require_platform_owner
from app.modules.common import utcnow

router = APIRouter(prefix="/admin", tags=["admin"])
AdminUserDep = Annotated[User, Depends(require_permission("admin:users"))]
PlatformOwnerDep = Annotated[User, Depends(require_platform_owner)]


def protect_platform_owner(target: User) -> None:
    if target.is_platform_owner:
        raise AppError(
            "platform_owner_protected",
            "A conta proprietária da plataforma não pode ser alterada por este painel.",
            status_code=403,
        )


async def serialize_admin_user(session: SessionDep, user: User) -> AdminUserOut:
    roles = list(
        (
            await session.scalars(
                select(Role.name)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user.id)
                .order_by(Role.name)
            )
        ).all()
    )
    connected_accounts = (
        await session.scalar(
            select(func.count(Account.id)).where(
                Account.owner_id == user.id,
                Account.removed_at.is_(None),
            )
        )
        or 0
    )
    campaigns_count = (
        await session.scalar(select(func.count(Campaign.id)).where(Campaign.owner_id == user.id))
        or 0
    )
    return build_admin_user_output(user, roles, connected_accounts, campaigns_count)


def build_admin_user_output(
    user: User,
    roles: list[str] | None = None,
    connected_accounts: int = 0,
    campaigns_count: int = 0,
) -> AdminUserOut:
    output = AdminUserOut.model_validate(user)
    output.roles = roles or []
    output.connected_accounts = connected_accounts
    output.campaigns_count = campaigns_count
    return output


@router.get("/users", response_model=list[AdminUserOut])
async def list_users(session: SessionDep, _actor: AdminUserDep) -> list[AdminUserOut]:
    account_totals = (
        select(
            Account.owner_id.label("owner_id"), func.count(Account.id).label("connected_accounts")
        )
        .where(Account.removed_at.is_(None))
        .group_by(Account.owner_id)
        .subquery()
    )
    campaign_totals = (
        select(
            Campaign.owner_id.label("owner_id"), func.count(Campaign.id).label("campaigns_count")
        )
        .group_by(Campaign.owner_id)
        .subquery()
    )
    role_totals = (
        select(UserRole.user_id.label("owner_id"), func.array_agg(Role.name).label("roles"))
        .join(Role, Role.id == UserRole.role_id)
        .group_by(UserRole.user_id)
        .subquery()
    )
    rows = (
        await session.execute(
            select(
                User,
                account_totals.c.connected_accounts,
                campaign_totals.c.campaigns_count,
                role_totals.c.roles,
            )
            .outerjoin(account_totals, account_totals.c.owner_id == User.id)
            .outerjoin(campaign_totals, campaign_totals.c.owner_id == User.id)
            .outerjoin(role_totals, role_totals.c.owner_id == User.id)
            .order_by(User.created_at.desc())
            .limit(500)
        )
    ).all()
    return [
        build_admin_user_output(
            row[0],
            row[3],
            row[1] or 0,
            row[2] or 0,
        )
        for row in rows
    ]


@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: uuid.UUID,
    payload: AdminUserUpdate,
    request: Request,
    session: SessionDep,
    actor: AdminUserDep,
) -> AdminUserOut:
    target = await session.get(User, user_id)
    if target is None or target.deleted_at is not None:
        raise AppError("user_not_found", "Usuário não encontrado.", status_code=404)
    if target.is_platform_owner and target.id != actor.id:
        protect_platform_owner(target)
    before = {"full_name": target.full_name, "timezone": target.timezone}
    if payload.full_name is not None:
        target.full_name = payload.full_name.strip() or None
    if payload.timezone is not None:
        target.timezone = payload.timezone
    await record_audit(
        session,
        action="user.update",
        target_type="user",
        target_id=str(target.id),
        actor_id=actor.id,
        owner_id=target.id,
        request_id=request.state.request_id,
        before=before,
        after={"full_name": target.full_name, "timezone": target.timezone},
    )
    await session.commit()
    return await serialize_admin_user(session, target)


@router.put("/users/{user_id}/admin", response_model=AdminUserOut)
async def set_user_admin(
    user_id: uuid.UUID,
    payload: AdminUserAdminUpdate,
    request: Request,
    session: SessionDep,
    actor: PlatformOwnerDep,
) -> AdminUserOut:
    target = await session.get(User, user_id)
    if target is None or target.deleted_at is not None:
        raise AppError("user_not_found", "Usuário não encontrado.", status_code=404)
    protect_platform_owner(target)
    admin_role = await session.scalar(select(Role).where(Role.name == "admin"))
    if admin_role is None:
        raise AppError(
            "admin_role_not_found", "Papel administrativo não configurado.", status_code=500
        )
    membership = await session.get(UserRole, {"user_id": target.id, "role_id": admin_role.id})
    before = {"roles": (await serialize_admin_user(session, target)).roles}
    if payload.is_admin and membership is None:
        session.add(UserRole(user_id=target.id, role_id=admin_role.id, granted_by=actor.id))
    elif not payload.is_admin and membership is not None:
        await session.delete(membership)
    else:
        return await serialize_admin_user(session, target)
    await record_audit(
        session,
        action="user.admin_granted" if payload.is_admin else "user.admin_revoked",
        target_type="user",
        target_id=str(target.id),
        actor_id=actor.id,
        owner_id=target.id,
        request_id=request.state.request_id,
        before=before,
        after={"is_admin": payload.is_admin},
    )
    await session.commit()
    return await serialize_admin_user(session, target)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    request: Request,
    session: SessionDep,
    actor: AdminUserDep,
) -> None:
    if user_id == actor.id:
        raise AppError("self_delete_forbidden", "Você não pode excluir a si mesmo.")
    target = await session.get(User, user_id)
    if target is None or target.deleted_at is not None:
        raise AppError("user_not_found", "Usuário não encontrado.", status_code=404)
    protect_platform_owner(target)
    now = utcnow()
    target.status = "deleted"
    target.deleted_at = now
    await session.execute(
        update(Campaign)
        .where(
            Campaign.owner_id == target.id,
            Campaign.state.in_(["scheduled", "running", "paused"]),
        )
        .values(state="cancelled", cancelled_at=now)
    )
    await session.execute(
        update(Job)
        .where(
            Job.owner_id == target.id,
            Job.state.in_(["planned", "queued", "publishing", "retry_scheduled"]),
        )
        .values(state="cancelled", updated_at=now)
    )
    await record_audit(
        session,
        action="user.delete_requested",
        target_type="user",
        target_id=str(target.id),
        actor_id=actor.id,
        owner_id=target.id,
        request_id=request.state.request_id,
        before={"status": "active"},
        after={"status": "deleted", "purge_after_days": 30},
    )
    await session.commit()


async def decide(
    target_id: uuid.UUID,
    action: str,
    payload: DecisionInput,
    actor: User,
    session: SessionDep,
    request_id: str | None,
) -> AdminUserOut:
    target = await session.get(User, target_id)
    if target is None:
        raise AppError("user_not_found", "Usuário não encontrado.", status_code=404)
    protect_platform_owner(target)
    now = utcnow()
    before = {"status": target.status}
    if action == "approve":
        target.status = "active"
        target.approved_at = now
        target.suspended_at = None
    elif action == "reject":
        target.status = "rejected"
    elif action == "suspend":
        if target.id == actor.id:
            raise AppError("self_suspend_forbidden", "Você não pode suspender a si mesmo.")
        target.status = "suspended"
        target.suspended_at = now
        await session.execute(
            update(Campaign)
            .where(
                Campaign.owner_id == target.id,
                Campaign.state.in_(["scheduled", "running"]),
            )
            .values(state="paused", paused_at=now)
        )
        await session.execute(
            update(Job)
            .where(
                Job.owner_id == target.id,
                Job.state.in_(["planned", "queued", "retry_scheduled"]),
            )
            .values(state="cancelled", updated_at=now)
        )
    elif action == "reactivate":
        target.status = "active"
        target.suspended_at = None
    else:
        raise AppError("invalid_admin_action", "Ação inválida.")
    session.add(
        Approval(
            user_id=target.id,
            decided_by=actor.id,
            decision=action,
            reason=payload.reason,
            decided_at=now,
        )
    )
    await record_audit(
        session,
        action=f"user.{action}",
        target_type="user",
        target_id=str(target.id),
        actor_id=actor.id,
        owner_id=target.id,
        request_id=request_id,
        before=before,
        after={"status": target.status},
    )
    await session.commit()
    return await serialize_admin_user(session, target)


@router.post("/users/{user_id}/approve", response_model=AdminUserOut)
async def approve_user(
    user_id: uuid.UUID,
    payload: DecisionInput,
    request: Request,
    session: SessionDep,
    actor: AdminUserDep,
) -> AdminUserOut:
    return await decide(user_id, "approve", payload, actor, session, request.state.request_id)


@router.post("/users/{user_id}/reject", response_model=AdminUserOut)
async def reject_user(
    user_id: uuid.UUID,
    payload: DecisionInput,
    request: Request,
    session: SessionDep,
    actor: AdminUserDep,
) -> AdminUserOut:
    return await decide(user_id, "reject", payload, actor, session, request.state.request_id)


@router.post("/users/{user_id}/suspend", response_model=AdminUserOut)
async def suspend_user(
    user_id: uuid.UUID,
    payload: DecisionInput,
    request: Request,
    session: SessionDep,
    actor: AdminUserDep,
) -> AdminUserOut:
    return await decide(user_id, "suspend", payload, actor, session, request.state.request_id)


@router.post("/users/{user_id}/reactivate", response_model=AdminUserOut)
async def reactivate_user(
    user_id: uuid.UUID,
    payload: DecisionInput,
    request: Request,
    session: SessionDep,
    actor: AdminUserDep,
) -> AdminUserOut:
    return await decide(user_id, "reactivate", payload, actor, session, request.state.request_id)


@router.get("/health")
async def deep_health(session: SessionDep, _actor: AdminUserDep) -> dict[str, object]:
    database, redis = await database_ready(), await redis_ready()
    scheduler: dict[str, object] = {"status": "unknown"}
    if database:
        state = await session.scalar(
            select(SchedulerState).where(SchedulerState.name == "publication-dispatcher")
        )
        if state:
            recent = bool(
                state.last_success_at
                and (datetime.now(UTC) - state.last_success_at).total_seconds() < 180
            )
            scheduler = {
                "status": "operational" if recent else "degraded",
                "last_success_at": state.last_success_at,
                "metadata": state.metadata_json,
            }
    return {
        "status": "operational" if database and redis else "degraded",
        "database": {"status": "operational" if database else "unavailable"},
        "redis": {"status": "operational" if redis else "unavailable"},
        "scheduler": scheduler,
    }


@router.get("/stats", response_model=AdminStatsOut)
async def platform_stats(session: SessionDep, _actor: AdminUserDep) -> AdminStatsOut:
    users = (
        await session.execute(
            select(
                func.count(User.id).filter(User.deleted_at.is_(None)),
                func.count(User.id).filter(User.status == "pending"),
            )
        )
    ).one()
    return AdminStatsOut(
        users=users[0],
        pending_users=users[1],
        connected_accounts=(
            await session.scalar(
                select(func.count(Account.id)).where(
                    Account.status == "connected",
                    Account.removed_at.is_(None),
                )
            )
            or 0
        ),
        campaigns=(await session.scalar(select(func.count(Campaign.id))) or 0),
        publications=(
            await session.scalar(select(func.count(Job.id)).where(Job.state == "succeeded")) or 0
        ),
        failed_publications=(
            await session.scalar(
                select(func.count(Job.id)).where(Job.state.in_(["failed_permanent", "dead_letter"]))
            )
            or 0
        ),
    )


@router.get("/plans", response_model=list[PlanOut])
async def list_plans(session: SessionDep, _actor: AdminUserDep) -> list[Plan]:
    return list((await session.scalars(select(Plan).order_by(Plan.price_monthly))).all())


@router.patch("/plans/{plan_id}", response_model=PlanOut)
async def update_plan(
    plan_id: uuid.UUID,
    payload: PlanUpdate,
    session: SessionDep,
    _actor: AdminUserDep,
) -> Plan:
    plan = await session.get(Plan, plan_id)
    if plan is None:
        raise AppError("plan_not_found", "Plano não encontrado.", status_code=404)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(plan, field, value)
    await session.commit()
    return plan


@router.put("/users/{user_id}/plan/{plan_id}", status_code=204)
async def assign_plan(
    user_id: uuid.UUID,
    plan_id: uuid.UUID,
    session: SessionDep,
    actor: AdminUserDep,
) -> None:
    target = await session.get(User, user_id)
    if target is None or await session.get(Plan, plan_id) is None:
        raise AppError("resource_not_found", "Usuário ou plano não encontrado.", status_code=404)
    if target.is_platform_owner and target.id != actor.id:
        protect_platform_owner(target)
    now = utcnow()
    await session.execute(
        update(UserPlan)
        .where(UserPlan.user_id == user_id, UserPlan.status == "active")
        .values(status="replaced", ends_at=now)
    )
    session.add(
        UserPlan(
            user_id=user_id,
            plan_id=plan_id,
            status="active",
            starts_at=now,
            overrides={},
        )
    )
    await session.commit()


@router.get("/audit-logs", response_model=list[AuditLogOut])
async def list_audit_logs(
    session: SessionDep,
    _actor: AdminUserDep,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[AuditLog]:
    return list(
        (
            await session.scalars(
                select(AuditLog).order_by(AuditLog.occurred_at.desc()).limit(limit)
            )
        ).all()
    )
