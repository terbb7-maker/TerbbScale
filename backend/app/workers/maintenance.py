import uuid
from datetime import timedelta

from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionFactory
from app.core.realtime import publish_user_event
from app.core.security import secret_box
from app.integrations.instagram import InstagramAPIError, InstagramClient
from app.models.instagram import Account, Proxy, Setting, Token
from app.models.operations import Notification
from app.modules.common import utcnow
from app.modules.proxies.service import (
    SCHEDULED_HEALTH_FAILURE_THRESHOLD,
    ProxyManager,
    account_proxy,
)


async def renew_expiring_tokens() -> int:
    now = utcnow()
    cutoff = now + timedelta(days=settings.TOKEN_RENEWAL_DAYS)
    renewed = 0
    async with SessionFactory() as session:
        tokens = list(
            (
                await session.scalars(
                    select(Token).where(
                        Token.revoked_at.is_(None),
                        Token.expires_at.is_not(None),
                        Token.expires_at <= cutoff,
                    )
                )
            ).all()
        )
        for token in tokens:
            account = await session.get(Account, token.account_id)
            setting = await session.scalar(
                select(Setting).where(Setting.owner_id == token.owner_id)
            )
            if (
                account is None
                or setting is None
                or not setting.instagram_app_id
                or not setting.instagram_app_secret_ciphertext
            ):
                continue
            try:
                app_secret = secret_box.decrypt(
                    setting.instagram_app_secret_ciphertext,
                    context=f"instagram-app:{token.owner_id}",
                )
                current = secret_box.decrypt(
                    token.token_ciphertext,
                    context=f"instagram-token:{token.owner_id}:{account.id}",
                )
                proxy = await account_proxy(session, account_id=account.id, owner_id=token.owner_id)
                async with ProxyManager().create_client(proxy) as http_client:
                    data = await InstagramClient(
                        app_id=setting.instagram_app_id,
                        app_secret=app_secret,
                        http_client=http_client,
                    ).refresh_token(current)
                token.token_ciphertext = secret_box.encrypt(
                    data.get("access_token", current),
                    context=f"instagram-token:{token.owner_id}:{account.id}",
                )
                token.refreshed_at = now
                token.expires_at = (
                    now + timedelta(seconds=int(data["expires_in"]))
                    if data.get("expires_in")
                    else token.expires_at
                )
                token.refresh_failures = 0
                account.token_expires_at = token.expires_at
                account.status = "connected"
                renewed += 1
            except InstagramAPIError as exc:
                token.refresh_failures += 1
                account.last_error_code = exc.error_class
                if not exc.retryable:
                    account.status = "expired"
                    session.add(
                        Notification(
                            owner_id=token.owner_id,
                            kind="token_expired",
                            title="Reconecte sua conta",
                            message=f"@{account.username} precisa ser reconectada.",
                            severity="error",
                            data={"account_id": str(account.id)},
                        )
                    )
        await session.commit()
    return renewed


async def check_active_proxies() -> int:
    """Refresh proxy health without blocking API request handlers."""
    checked = 0
    manager = ProxyManager()
    owner_ids: set[uuid.UUID] = set()
    async with SessionFactory() as session:
        proxies = list(
            (
                await session.scalars(
                    select(Proxy)
                    .where(Proxy.is_active.is_(True))
                    .order_by(Proxy.last_check.asc().nullsfirst())
                )
            ).all()
        )
        results = await manager.test_many(proxies)
        for proxy, result in zip(proxies, results, strict=True):
            manager.apply_check(
                proxy,
                result,
                failure_threshold=SCHEDULED_HEALTH_FAILURE_THRESHOLD,
            )
            owner_ids.add(proxy.owner_id)
            checked += 1
        await session.commit()
    for owner_id in owner_ids:
        await publish_user_event(owner_id, "proxy.health_updated", {})
    return checked
