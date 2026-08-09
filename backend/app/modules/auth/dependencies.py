import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.core.errors import AppError
from app.core.security import AuthenticatedUser, verify_supabase_token
from app.models.identity import Permission, Role, RolePermission, User, UserRole

bearer = HTTPBearer(auto_error=False)
SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_identity(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError("not_authenticated", "Autenticação necessária.", status_code=401)
    try:
        return await verify_supabase_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise AppError("invalid_session", "Sessão inválida ou expirada.", status_code=401) from exc


IdentityDep = Annotated[AuthenticatedUser, Depends(get_identity)]


async def get_current_user(identity: IdentityDep, session: SessionDep) -> User:
    user_id = uuid.UUID(identity.id)
    user = await session.get(User, user_id)
    bootstrap_admin = bool(
        settings.BOOTSTRAP_ADMIN_EMAIL
        and identity.email
        and identity.email.casefold() == settings.BOOTSTRAP_ADMIN_EMAIL.casefold()
    )
    if user is None:
        user = User(
            id=user_id,
            email=identity.email,
            status="active" if bootstrap_admin else "pending",
            timezone="UTC",
            locale="pt-BR",
        )
        session.add(user)
        await session.flush()
    elif bootstrap_admin and user.status == "pending":
        user.status = "active"
    if bootstrap_admin:
        admin_role = await session.scalar(select(Role).where(Role.name == "admin"))
        if admin_role is not None:
            existing_role = await session.get(
                UserRole,
                {"user_id": user.id, "role_id": admin_role.id},
            )
            if existing_role is None:
                session.add(UserRole(user_id=user.id, role_id=admin_role.id))
    now = datetime.now(UTC)
    if user.last_seen_at is None or user.last_seen_at < now - timedelta(minutes=5):
        user.last_seen_at = now
    if session.new or session.dirty:
        await session.commit()
        await session.refresh(user)
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def require_active_user(user: CurrentUserDep) -> User:
    if user.status != "active":
        code = "approval_pending" if user.status == "pending" else "account_not_active"
        raise AppError(code, "Sua conta ainda não está ativa.", status_code=403)
    return user


ActiveUserDep = Annotated[User, Depends(require_active_user)]


async def permission_codes(user_id: uuid.UUID, session: AsyncSession) -> set[str]:
    query = (
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user_id)
    )
    return set((await session.scalars(query)).all())


def require_permission(code: str) -> Callable[..., object]:
    async def dependency(user: ActiveUserDep, session: SessionDep) -> User:
        if user.is_platform_owner:
            return user
        permissions = await permission_codes(user.id, session)
        if code not in permissions:
            raise AppError("permission_denied", "Permissão insuficiente.", status_code=403)
        return user

    return dependency


async def require_platform_owner(user: ActiveUserDep) -> User:
    if not user.is_platform_owner:
        raise AppError(
            "platform_owner_required",
            "Apenas o proprietário da plataforma pode executar esta ação.",
            status_code=403,
        )
    return user
