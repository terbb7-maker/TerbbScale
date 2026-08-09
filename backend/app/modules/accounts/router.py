import hashlib
import uuid
from datetime import timedelta

import httpx
from fastapi import APIRouter, Query
from sqlalchemy import delete, select, update

from app.core.errors import AppError
from app.core.realtime import publish_user_event
from app.core.security import new_oauth_state, secret_box
from app.integrations.instagram import InstagramAPIError, InstagramClient
from app.models.campaigns import Job
from app.models.instagram import (
    Account,
    AccountHealthCheck,
    AccountProxy,
    OAuthState,
    Proxy,
    Setting,
    Token,
)
from app.models.operations import Notification
from app.modules.accounts.health import apply_health_assessment, classify_instagram_error
from app.modules.accounts.schemas import (
    AccountBulkRemoveInput,
    AccountBulkRemoveOut,
    AccountHealthCheckOut,
    AccountOut,
    AccountProxyPoolInput,
    AccountProxyPoolItem,
    AccountProxyPoolOut,
    ConnectResponse,
    OAuthCallbackInput,
)
from app.modules.audit import record_audit
from app.modules.auth.dependencies import ActiveUserDep, SessionDep
from app.modules.common import utcnow
from app.modules.proxies.schemas import AccountProxyInput, BulkAccountProxyInput
from app.modules.proxies.service import ProxyManager, account_proxy
from app.modules.settings.router import REQUIRED_INSTAGRAM_SCOPES

router = APIRouter(prefix="/accounts", tags=["accounts"])


async def tenant_setting(owner_id: uuid.UUID, session: SessionDep) -> Setting:
    setting = await session.scalar(select(Setting).where(Setting.owner_id == owner_id))
    if (
        setting is None
        or not setting.instagram_app_id
        or not setting.instagram_app_secret_ciphertext
        or not setting.redirect_uri
    ):
        raise AppError(
            "instagram_app_not_configured",
            "Configure seu Instagram App antes de conectar uma conta.",
            status_code=409,
        )
    return setting


def instagram_client(
    setting: Setting, http_client: httpx.AsyncClient | None = None
) -> InstagramClient:
    secret = secret_box.decrypt(
        setting.instagram_app_secret_ciphertext or "",
        context=f"instagram-app:{setting.owner_id}",
    )
    return InstagramClient(
        app_id=setting.instagram_app_id or "",
        app_secret=secret,
        http_client=http_client,
    )


@router.get("", response_model=list[AccountOut])
async def list_accounts(
    user: ActiveUserDep,
    session: SessionDep,
    status: str | None = Query(default=None),
) -> list[AccountOut]:
    query = (
        select(Account)
        .where(Account.owner_id == user.id, Account.removed_at.is_(None))
        .order_by(Account.created_at.desc())
        .limit(200)
    )
    if status:
        query = query.where(Account.status == status)
    accounts = list((await session.scalars(query)).all())
    links_by_account: dict[uuid.UUID, list[tuple[AccountProxy, Proxy]]] = {}
    if accounts:
        rows = (
            await session.execute(
                select(AccountProxy, Proxy)
                .join(Proxy, Proxy.id == AccountProxy.proxy_id)
                .where(AccountProxy.account_id.in_([account.id for account in accounts]))
                .order_by(AccountProxy.account_id, AccountProxy.priority)
            )
        ).all()
        for link, proxy in rows:
            links_by_account.setdefault(link.account_id, []).append((link, proxy))
    return [
        AccountOut.model_validate(
            {
                **{
                    field: getattr(account, field)
                    for field in AccountOut.model_fields
                    if hasattr(account, field)
                },
                "proxy_id": links_by_account.get(account.id, [(None, None)])[0][1].id
                if links_by_account.get(account.id)
                else None,
                "proxy_name": links_by_account.get(account.id, [(None, None)])[0][1].name
                if links_by_account.get(account.id)
                else None,
                "proxy_status": links_by_account.get(account.id, [(None, None)])[0][1].status
                if links_by_account.get(account.id)
                else None,
                "proxy_pool_size": len(links_by_account.get(account.id, [])),
            }
        )
        for account in accounts
    ]


async def owned_account(account_id: uuid.UUID, owner_id: uuid.UUID, session: SessionDep) -> Account:
    account = await session.scalar(
        select(Account).where(
            Account.id == account_id,
            Account.owner_id == owner_id,
            Account.removed_at.is_(None),
        )
    )
    if account is None:
        raise AppError("account_not_found", "Conta não encontrada.", status_code=404)
    return account


async def proxy_pool_out(account: Account, session: SessionDep) -> AccountProxyPoolOut:
    rows = (
        await session.execute(
            select(AccountProxy, Proxy)
            .join(Proxy, Proxy.id == AccountProxy.proxy_id)
            .where(AccountProxy.account_id == account.id)
            .order_by(AccountProxy.priority)
        )
    ).all()
    return AccountProxyPoolOut(
        account_id=account.id,
        rotation_mode=account.proxy_rotation_mode,
        rotate_every=account.proxy_rotation_every,
        counter=account.proxy_rotation_counter,
        current_proxy_id=account.proxy_rotation_current_proxy_id,
        proxies=[
            AccountProxyPoolItem(
                id=proxy.id,
                name=proxy.name,
                status=proxy.status,
                is_active=link.is_active and proxy.is_active,
                priority=link.priority,
                last_selected_at=link.last_selected_at,
                cooldown_until=proxy.cooldown_until,
            )
            for link, proxy in rows
        ],
    )


@router.post("/connect", response_model=ConnectResponse)
async def connect_account(user: ActiveUserDep, session: SessionDep) -> ConnectResponse:
    setting = await tenant_setting(user.id, session)
    setting.scopes = list(dict.fromkeys([*setting.scopes, *sorted(REQUIRED_INSTAGRAM_SCOPES)]))
    state = new_oauth_state()
    now = utcnow()
    session.add(
        OAuthState(
            owner_id=user.id,
            state_hash=hashlib.sha256(state.encode()).hexdigest(),
            expires_at=now + timedelta(minutes=10),
            created_at=now,
        )
    )
    await session.commit()
    url = instagram_client(setting).authorization_url(
        redirect_uri=setting.redirect_uri or "",
        scopes=setting.scopes,
        state=state,
    )
    return ConnectResponse(authorization_url=url, expires_in=600)


@router.post("/oauth/callback", response_model=AccountOut)
async def oauth_callback(payload: OAuthCallbackInput, session: SessionDep) -> Account:
    now = utcnow()
    state_hash = hashlib.sha256(payload.state.encode()).hexdigest()
    oauth_state = await session.scalar(
        select(OAuthState).where(
            OAuthState.state_hash == state_hash,
            OAuthState.expires_at > now,
            OAuthState.consumed_at.is_(None),
        )
    )
    if oauth_state is None:
        raise AppError("invalid_oauth_state", "Autorização inválida ou expirada.", status_code=400)
    oauth_state.consumed_at = now
    setting = await tenant_setting(oauth_state.owner_id, session)
    try:
        async with ProxyManager().create_client(None) as http_client:
            client = instagram_client(setting, http_client)
            short = await client.exchange_code(
                code=payload.code, redirect_uri=setting.redirect_uri or ""
            )
            exchanged = await client.exchange_long_lived_token(short["access_token"])
            token_value = exchanged.get("access_token", short["access_token"])
            user_id = str(short.get("user_id") or short.get("id"))
            profile = await client.profile(user_id, token_value)
    except InstagramAPIError as exc:
        await session.rollback()
        raise AppError(exc.error_class, str(exc), status_code=502) from exc

    expires_at = (
        now + timedelta(seconds=int(exchanged.get("expires_in", 0)))
        if exchanged.get("expires_in")
        else None
    )
    account = await session.scalar(
        select(Account).where(
            Account.owner_id == oauth_state.owner_id,
            Account.instagram_user_id == profile.id,
            Account.removed_at.is_(None),
        )
    )
    if account is None:
        account = Account(
            owner_id=oauth_state.owner_id,
            instagram_user_id=profile.id,
            username=profile.username,
            display_name=profile.name,
            profile_picture_url=profile.profile_picture_url,
            account_type=profile.account_type,
            status="connected",
            health_status="operational",
            health_confidence="confirmed",
            health_source="oauth",
            health_checked_at=now,
            health_last_success_at=now,
            health_next_check_at=now + timedelta(minutes=3),
            health_message="A conta respondeu normalmente durante a conexão.",
            granted_scopes=setting.scopes,
            token_expires_at=expires_at,
            connected_at=now,
        )
        session.add(account)
        await session.flush()
    else:
        account.username = profile.username
        account.display_name = profile.name
        account.profile_picture_url = profile.profile_picture_url
        account.account_type = profile.account_type
        account.status = "connected"
        account.health_status = "operational"
        account.health_confidence = "confirmed"
        account.health_source = "oauth"
        account.health_checked_at = now
        account.health_last_success_at = now
        account.health_next_check_at = now + timedelta(minutes=3)
        account.health_consecutive_failures = 0
        account.health_error_code = None
        account.health_error_subcode = None
        account.health_message = "A conta respondeu normalmente durante a reconexão."
        account.health_action_required = None
        account.last_error_code = None
        account.granted_scopes = setting.scopes
        account.token_expires_at = expires_at
        account.connected_at = now
    await session.execute(
        update(Token)
        .where(Token.account_id == account.id, Token.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    session.add(
        Token(
            owner_id=oauth_state.owner_id,
            account_id=account.id,
            token_ciphertext=secret_box.encrypt(
                token_value,
                context=f"instagram-token:{oauth_state.owner_id}:{account.id}",
            ),
            scopes=setting.scopes,
            issued_at=now,
            expires_at=expires_at,
        )
    )
    await session.execute(
        update(Notification)
        .where(
            Notification.owner_id == oauth_state.owner_id,
            Notification.kind == "insights_permission_required",
            Notification.read_at.is_(None),
        )
        .values(read_at=now)
    )
    await session.commit()
    await session.refresh(account)
    from app.workers.tasks import collect_insights_task

    collect_insights_task.apply_async(queue="maintenance")
    return account


@router.post("/{account_id}/refresh-token", response_model=AccountOut)
async def refresh_account_token(
    account_id: uuid.UUID,
    user: ActiveUserDep,
    session: SessionDep,
) -> Account:
    account = await session.scalar(
        select(Account).where(
            Account.id == account_id,
            Account.owner_id == user.id,
            Account.removed_at.is_(None),
        )
    )
    if account is None:
        raise AppError("account_not_found", "Conta não encontrada.", status_code=404)
    token = await session.scalar(
        select(Token)
        .where(Token.account_id == account.id, Token.revoked_at.is_(None))
        .order_by(Token.created_at.desc())
    )
    if token is None:
        raise AppError("token_not_found", "Token não encontrado.", status_code=409)
    setting = await tenant_setting(user.id, session)
    current = secret_box.decrypt(
        token.token_ciphertext,
        context=f"instagram-token:{user.id}:{account.id}",
    )
    try:
        proxy = await account_proxy(session, account_id=account.id, owner_id=user.id)
        async with ProxyManager().create_client(proxy) as http_client:
            data = await instagram_client(setting, http_client).refresh_token(current)
    except InstagramAPIError as exc:
        account.last_error_code = exc.error_class
        assessment = classify_instagram_error(
            exc,
            consecutive_failures=account.health_consecutive_failures + 1,
            allow_inferred_suspension=False,
        )
        if assessment is not None:
            await apply_health_assessment(
                session,
                account,
                assessment,
                source="token_refresh",
            )
        await session.commit()
        if assessment is not None:
            await publish_user_event(
                user.id,
                "account.health_updated",
                {"account_id": str(account.id), "source": "token_refresh"},
            )
        raise AppError(exc.error_class, str(exc), status_code=502) from exc
    now = utcnow()
    token.token_ciphertext = secret_box.encrypt(
        data.get("access_token", current),
        context=f"instagram-token:{user.id}:{account.id}",
    )
    token.refreshed_at = now
    token.expires_at = (
        now + timedelta(seconds=int(data["expires_in"]))
        if data.get("expires_in")
        else token.expires_at
    )
    account.token_expires_at = token.expires_at
    account.status = "connected"
    account.health_status = "checking"
    account.health_confidence = "unknown"
    account.health_source = "token_refresh"
    account.health_next_check_at = now + timedelta(minutes=5)
    account.last_error_code = None
    await session.commit()
    from app.workers.tasks import check_account_health_task

    check_account_health_task.apply_async(
        args=[str(account.id), "token_refresh"],
        queue="maintenance",
    )
    return account


@router.post("/{account_id}/health-check", status_code=202)
async def request_account_health_check(
    account_id: uuid.UUID,
    user: ActiveUserDep,
    session: SessionDep,
) -> dict[str, str]:
    account = await owned_account(account_id, user.id, session)
    now = utcnow()
    account.health_status = "checking"
    account.health_confidence = "unknown"
    account.health_source = "manual"
    account.health_next_check_at = now + timedelta(minutes=5)
    await session.commit()
    from app.workers.tasks import check_account_health_task

    check_account_health_task.apply_async(
        args=[str(account.id), "manual"],
        queue="maintenance",
    )
    return {"status": "checking"}


@router.get("/{account_id}/health-checks", response_model=list[AccountHealthCheckOut])
async def list_account_health_checks(
    account_id: uuid.UUID,
    user: ActiveUserDep,
    session: SessionDep,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[AccountHealthCheck]:
    account = await owned_account(account_id, user.id, session)
    return list(
        (
            await session.scalars(
                select(AccountHealthCheck)
                .where(
                    AccountHealthCheck.account_id == account.id,
                    AccountHealthCheck.owner_id == user.id,
                )
                .order_by(AccountHealthCheck.checked_at.desc())
                .limit(limit)
            )
        ).all()
    )


@router.post("/{account_id}/proxy", status_code=204)
async def set_account_proxy(
    account_id: uuid.UUID,
    payload: AccountProxyInput,
    user: ActiveUserDep,
    session: SessionDep,
) -> None:
    account = await owned_account(account_id, user.id, session)
    if payload.proxy_id is None:
        await session.execute(delete(AccountProxy).where(AccountProxy.account_id == account.id))
        account.proxy_rotation_current_proxy_id = None
        account.proxy_rotation_counter = 0
    else:
        proxy = await session.scalar(
            select(Proxy).where(Proxy.id == payload.proxy_id, Proxy.owner_id == user.id)
        )
        if proxy is None:
            raise AppError("proxy_not_found", "Proxy não encontrado.", status_code=404)
        await session.execute(delete(AccountProxy).where(AccountProxy.account_id == account.id))
        session.add(AccountProxy(account_id=account.id, proxy_id=proxy.id, priority=1))
        account.proxy_rotation_mode = "fixed"
        account.proxy_rotation_every = 1
        account.proxy_rotation_counter = 0
        account.proxy_rotation_current_proxy_id = proxy.id
    await session.commit()


@router.delete("/{account_id}/proxy", status_code=204)
async def remove_account_proxy(
    account_id: uuid.UUID, user: ActiveUserDep, session: SessionDep
) -> None:
    account = await owned_account(account_id, user.id, session)
    await session.execute(delete(AccountProxy).where(AccountProxy.account_id == account.id))
    account.proxy_rotation_current_proxy_id = None
    account.proxy_rotation_counter = 0
    await session.commit()


@router.get("/{account_id}/proxy-pool", response_model=AccountProxyPoolOut)
async def get_account_proxy_pool(
    account_id: uuid.UUID, user: ActiveUserDep, session: SessionDep
) -> AccountProxyPoolOut:
    return await proxy_pool_out(await owned_account(account_id, user.id, session), session)


@router.put("/{account_id}/proxy-pool", response_model=AccountProxyPoolOut)
async def set_account_proxy_pool(
    account_id: uuid.UUID,
    payload: AccountProxyPoolInput,
    user: ActiveUserDep,
    session: SessionDep,
) -> AccountProxyPoolOut:
    account = await owned_account(account_id, user.id, session)
    proxies = list(
        (
            await session.scalars(
                select(Proxy).where(
                    Proxy.id.in_(payload.proxy_ids),
                    Proxy.owner_id == user.id,
                    Proxy.is_active.is_(True),
                )
            )
        ).all()
    )
    if len(proxies) != len(payload.proxy_ids):
        raise AppError(
            "proxy_not_found",
            "Uma ou mais proxies não existem, não pertencem ao usuário ou estão inativas.",
            status_code=404,
        )
    await session.execute(delete(AccountProxy).where(AccountProxy.account_id == account.id))
    for priority, proxy_id in enumerate(payload.proxy_ids, start=1):
        session.add(AccountProxy(account_id=account.id, proxy_id=proxy_id, priority=priority))
    account.proxy_rotation_mode = payload.rotation_mode
    account.proxy_rotation_every = payload.rotate_every
    account.proxy_rotation_counter = 0
    account.proxy_rotation_current_proxy_id = None
    await session.commit()
    return await proxy_pool_out(account, session)


@router.post("/proxy/bulk", status_code=204)
async def bulk_set_account_proxy(
    payload: BulkAccountProxyInput, user: ActiveUserDep, session: SessionDep
) -> None:
    account_ids = list(dict.fromkeys(payload.account_ids))
    accounts = list(
        (
            await session.scalars(
                select(Account).where(
                    Account.id.in_(account_ids),
                    Account.owner_id == user.id,
                    Account.removed_at.is_(None),
                )
            )
        ).all()
    )
    if len(accounts) != len(account_ids):
        raise AppError(
            "account_not_found", "Uma ou mais contas não foram encontradas.", status_code=404
        )
    if payload.proxy_id is None:
        await session.execute(delete(AccountProxy).where(AccountProxy.account_id.in_(account_ids)))
        await session.execute(
            update(Account)
            .where(Account.id.in_(account_ids))
            .values(proxy_rotation_current_proxy_id=None, proxy_rotation_counter=0)
        )
    else:
        proxy = await session.scalar(
            select(Proxy).where(Proxy.id == payload.proxy_id, Proxy.owner_id == user.id)
        )
        if proxy is None:
            raise AppError("proxy_not_found", "Proxy não encontrado.", status_code=404)
        for account in accounts:
            await session.execute(delete(AccountProxy).where(AccountProxy.account_id == account.id))
            session.add(AccountProxy(account_id=account.id, proxy_id=proxy.id, priority=1))
            account.proxy_rotation_mode = "fixed"
            account.proxy_rotation_every = 1
            account.proxy_rotation_counter = 0
            account.proxy_rotation_current_proxy_id = proxy.id
    await session.commit()


@router.post("/bulk-remove", response_model=AccountBulkRemoveOut)
async def bulk_remove_accounts(
    payload: AccountBulkRemoveInput,
    user: ActiveUserDep,
    session: SessionDep,
) -> AccountBulkRemoveOut:
    account_ids = payload.account_ids
    owned_ids = set(
        (
            await session.scalars(
                select(Account.id).where(
                    Account.id.in_(account_ids),
                    Account.owner_id == user.id,
                    Account.removed_at.is_(None),
                )
            )
        ).all()
    )
    if owned_ids != set(account_ids):
        raise AppError(
            "account_not_found",
            "Uma ou mais contas não foram encontradas.",
            status_code=404,
        )
    now = utcnow()
    await session.execute(
        update(Account)
        .where(Account.id.in_(account_ids), Account.owner_id == user.id)
        .values(status="removed", removed_at=now)
    )
    await session.execute(
        update(Token)
        .where(Token.account_id.in_(account_ids), Token.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    await session.execute(
        update(Job)
        .where(
            Job.owner_id == user.id,
            Job.account_id.in_(account_ids),
            Job.state.in_(["planned", "queued", "retry_scheduled"]),
        )
        .values(state="cancelled", updated_at=now)
    )
    await record_audit(
        session,
        action="accounts_bulk_removed",
        target_type="account",
        actor_id=user.id,
        owner_id=user.id,
        after={"removed": len(account_ids), "account_ids": [str(item) for item in account_ids]},
    )
    await session.commit()
    return AccountBulkRemoveOut(removed=len(account_ids))


@router.delete("/{account_id}", status_code=204)
async def remove_account(
    account_id: uuid.UUID,
    user: ActiveUserDep,
    session: SessionDep,
) -> None:
    account = await session.scalar(
        select(Account).where(
            Account.id == account_id,
            Account.owner_id == user.id,
            Account.removed_at.is_(None),
        )
    )
    if account is None:
        raise AppError("account_not_found", "Conta não encontrada.", status_code=404)
    now = utcnow()
    account.status = "removed"
    account.removed_at = now
    await session.execute(
        update(Token)
        .where(Token.account_id == account.id, Token.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    await session.execute(
        update(Job)
        .where(
            Job.account_id == account.id,
            Job.state.in_(["planned", "queued", "retry_scheduled"]),
        )
        .values(state="cancelled", updated_at=now)
    )
    await session.commit()
