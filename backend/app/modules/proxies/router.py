import uuid

from fastapi import APIRouter, status
from sqlalchemy import delete, func, select, update

from app.core.errors import AppError
from app.core.security import secret_box
from app.models.campaigns import Campaign
from app.models.instagram import AccountProxy, Proxy
from app.modules.audit import record_audit
from app.modules.auth.dependencies import ActiveUserDep, SessionDep
from app.modules.proxies.schemas import (
    ProxyBulkRemoveInput,
    ProxyBulkRemoveOut,
    ProxyImportError,
    ProxyImportInput,
    ProxyImportOut,
    ProxyInput,
    ProxyOut,
    ProxyTestAllOut,
    ProxyTestOut,
    ProxyUpdate,
)
from app.modules.proxies.service import ProxyCheckResult, ProxyManager, parse_proxy_entry

router = APIRouter(prefix="/proxies", tags=["proxies"])


def proxy_out(proxy: Proxy, accounts_using: int = 0) -> ProxyOut:
    return ProxyOut(
        id=proxy.id,
        name=proxy.name,
        protocol=proxy.protocol,
        host=proxy.host,
        port=proxy.port,
        username=proxy.username,
        password_configured=bool(proxy.password_ciphertext),
        country=proxy.country,
        notes=proxy.notes,
        is_active=proxy.is_active,
        status=proxy.status,
        last_error=proxy.last_error,
        last_check=proxy.last_check,
        latency_ms=proxy.latency_ms,
        public_ip=proxy.public_ip,
        cooldown_until=proxy.cooldown_until,
        consecutive_failures=proxy.consecutive_failures,
        accounts_using=accounts_using,
        created_at=proxy.created_at,
        updated_at=proxy.updated_at,
    )


async def owned_proxy(proxy_id: uuid.UUID, user_id: uuid.UUID, session: SessionDep) -> Proxy:
    proxy = await session.scalar(
        select(Proxy).where(
            Proxy.id == proxy_id,
            Proxy.owner_id == user_id,
            Proxy.removed_at.is_(None),
        )
    )
    if proxy is None:
        raise AppError("proxy_not_found", "Proxy não encontrado.", status_code=404)
    return proxy


def test_out(proxy_id: uuid.UUID, result: ProxyCheckResult) -> ProxyTestOut:
    return ProxyTestOut(
        proxy_id=proxy_id,
        status=result.status,
        public_ip=result.public_ip,
        latency_ms=result.latency_ms,
        checked_at=result.checked_at,  # type: ignore[arg-type]
        error=result.error,
    )


@router.get("", response_model=list[ProxyOut])
async def list_proxies(user: ActiveUserDep, session: SessionDep) -> list[ProxyOut]:
    rows = (
        await session.execute(
            select(Proxy, func.count(AccountProxy.account_id).label("accounts_using"))
            .outerjoin(AccountProxy, AccountProxy.proxy_id == Proxy.id)
            .where(Proxy.owner_id == user.id, Proxy.removed_at.is_(None))
            .group_by(Proxy.id)
            .order_by(Proxy.created_at.desc())
            .limit(500)
        )
    ).all()
    return [proxy_out(proxy, int(count)) for proxy, count in rows]


@router.post("", response_model=ProxyOut, status_code=status.HTTP_201_CREATED)
async def create_proxy(payload: ProxyInput, user: ActiveUserDep, session: SessionDep) -> ProxyOut:
    proxy = Proxy(owner_id=user.id, **payload.model_dump(exclude={"password"}))
    session.add(proxy)
    await session.flush()
    if payload.password:
        proxy.password_ciphertext = secret_box.encrypt(
            payload.password, context=ProxyManager().password_context(proxy)
        )
    await record_audit(
        session,
        action="proxy_created",
        target_type="proxy",
        actor_id=user.id,
        owner_id=user.id,
        target_id=str(proxy.id),
        after={"name": proxy.name, "protocol": proxy.protocol},
    )
    await session.commit()
    await session.refresh(proxy)
    return proxy_out(proxy)


@router.post("/import", response_model=ProxyImportOut, status_code=status.HTTP_201_CREATED)
async def import_proxies(
    payload: ProxyImportInput, user: ActiveUserDep, session: SessionDep
) -> ProxyImportOut:
    """Import one or more lines in the `host:port:username:password` format."""
    created: list[Proxy] = []
    errors: list[ProxyImportError] = []
    manager = ProxyManager()
    for line_number, raw_entry in enumerate(payload.entries.splitlines(), start=1):
        if not raw_entry.strip():
            continue
        try:
            entry = parse_proxy_entry(raw_entry)
        except ValueError as exc:
            errors.append(ProxyImportError(line=line_number, error=str(exc)))
            continue
        proxy = Proxy(
            owner_id=user.id,
            name=f"{payload.name_prefix or 'Proxy'} {line_number} · {entry.host}:{entry.port}"[
                :160
            ],
            protocol=payload.protocol,
            host=entry.host,
            port=entry.port,
            username=entry.username,
            country=payload.country,
            is_active=payload.is_active,
        )
        session.add(proxy)
        await session.flush()
        proxy.password_ciphertext = secret_box.encrypt(
            entry.password, context=manager.password_context(proxy)
        )
        created.append(proxy)
    await record_audit(
        session,
        action="proxies_imported",
        target_type="proxy",
        actor_id=user.id,
        owner_id=user.id,
        after={"created": len(created), "rejected": len(errors)},
    )
    await session.commit()
    for proxy in created:
        await session.refresh(proxy)
    return ProxyImportOut(
        created=len(created),
        rejected=len(errors),
        proxies=[proxy_out(proxy) for proxy in created],
        errors=errors,
    )


@router.put("/{proxy_id}", response_model=ProxyOut)
async def update_proxy(
    proxy_id: uuid.UUID, payload: ProxyUpdate, user: ActiveUserDep, session: SessionDep
) -> ProxyOut:
    proxy = await owned_proxy(proxy_id, user.id, session)
    before = {
        "name": proxy.name,
        "protocol": proxy.protocol,
        "host": proxy.host,
        "port": proxy.port,
    }
    values = payload.model_dump(exclude_unset=True, exclude={"password"})
    for key, value in values.items():
        setattr(proxy, key, value)
    if "password" in payload.model_fields_set:
        proxy.password_ciphertext = (
            secret_box.encrypt(payload.password, context=ProxyManager().password_context(proxy))
            if payload.password
            else None
        )
    proxy.status = "unknown"
    proxy.last_error = None
    await record_audit(
        session,
        action="proxy_updated",
        target_type="proxy",
        actor_id=user.id,
        owner_id=user.id,
        target_id=str(proxy.id),
        before=before,
        after={
            "name": proxy.name,
            "protocol": proxy.protocol,
            "host": proxy.host,
            "port": proxy.port,
        },
    )
    await session.commit()
    await session.refresh(proxy)
    count = await session.scalar(
        select(func.count()).select_from(AccountProxy).where(AccountProxy.proxy_id == proxy.id)
    )
    return proxy_out(proxy, int(count or 0))


@router.post("/bulk-remove", response_model=ProxyBulkRemoveOut)
async def bulk_remove_proxies(
    payload: ProxyBulkRemoveInput,
    user: ActiveUserDep,
    session: SessionDep,
) -> ProxyBulkRemoveOut:
    proxy_ids = list(dict.fromkeys(payload.proxy_ids))
    owned_ids = set(
        (
            await session.scalars(
                select(Proxy.id).where(
                    Proxy.id.in_(proxy_ids),
                    Proxy.owner_id == user.id,
                    Proxy.removed_at.is_(None),
                )
            )
        ).all()
    )
    if owned_ids != set(proxy_ids):
        raise AppError(
            "proxy_not_found",
            "Uma ou mais proxies não foram encontradas.",
            status_code=404,
        )
    active_campaign = await session.scalar(
        select(Campaign.id)
        .where(
            Campaign.owner_id == user.id,
            Campaign.proxy_id.in_(proxy_ids),
            Campaign.state.in_(["scheduled", "running", "paused"]),
        )
        .limit(1)
    )
    if active_campaign:
        raise AppError(
            "proxy_in_use",
            "Uma ou mais proxies estão em campanhas ativas. "
            "Pause ou finalize essas campanhas primeiro.",
            status_code=409,
        )
    await session.execute(delete(AccountProxy).where(AccountProxy.proxy_id.in_(proxy_ids)))
    await session.execute(
        update(Proxy)
        .where(Proxy.id.in_(proxy_ids), Proxy.owner_id == user.id)
        .values(is_active=False, removed_at=func.now())
    )
    await record_audit(
        session,
        action="proxies_bulk_removed",
        target_type="proxy",
        actor_id=user.id,
        owner_id=user.id,
        after={"removed": len(proxy_ids), "proxy_ids": [str(item) for item in proxy_ids]},
    )
    await session.commit()
    return ProxyBulkRemoveOut(removed=len(proxy_ids))


@router.delete("/{proxy_id}", status_code=204)
async def delete_proxy(proxy_id: uuid.UUID, user: ActiveUserDep, session: SessionDep) -> None:
    proxy = await owned_proxy(proxy_id, user.id, session)
    active_campaign = await session.scalar(
        select(Campaign.id)
        .where(
            Campaign.owner_id == user.id,
            Campaign.proxy_id == proxy.id,
            Campaign.state.in_(["scheduled", "running", "paused"]),
        )
        .limit(1)
    )
    if active_campaign:
        raise AppError("proxy_in_use", "O proxy está em uma campanha ativa.", status_code=409)
    await session.execute(delete(AccountProxy).where(AccountProxy.proxy_id == proxy.id))
    await record_audit(
        session,
        action="proxy_deleted",
        target_type="proxy",
        actor_id=user.id,
        owner_id=user.id,
        target_id=str(proxy.id),
        before={"name": proxy.name, "host": proxy.host},
    )
    proxy.is_active = False
    proxy.removed_at = func.now()
    await session.commit()


@router.post("/{proxy_id}/test", response_model=ProxyTestOut)
async def test_proxy(proxy_id: uuid.UUID, user: ActiveUserDep, session: SessionDep) -> ProxyTestOut:
    proxy = await owned_proxy(proxy_id, user.id, session)
    result = await ProxyManager().test(proxy)
    ProxyManager().apply_check(proxy, result)
    await session.commit()
    return test_out(proxy.id, result)


@router.post("/test-all", response_model=ProxyTestAllOut)
async def test_all_proxies(user: ActiveUserDep, session: SessionDep) -> ProxyTestAllOut:
    proxies = list(
        (
            await session.scalars(
                select(Proxy).where(Proxy.owner_id == user.id, Proxy.removed_at.is_(None))
            )
        ).all()
    )
    manager = ProxyManager()
    results: list[ProxyTestOut] = []
    checks = await manager.test_many(proxies)
    for proxy, result in zip(proxies, checks, strict=True):
        manager.apply_check(proxy, result)
        results.append(test_out(proxy.id, result))
    await session.commit()
    return ProxyTestAllOut(
        tested=len(results),
        online=sum(item.status == "online" for item in results),
        offline=sum(item.status == "offline" for item in results),
        results=results,
    )
