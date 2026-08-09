import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import SessionFactory
from app.core.logging import logger
from app.core.realtime import publish_user_event
from app.core.security import secret_box
from app.integrations.instagram import InstagramAPIError, InstagramClient
from app.models.campaigns import Campaign, Job
from app.models.instagram import Account, Setting, Token
from app.models.operations import InsightSnapshot, Notification
from app.modules.common import utcnow
from app.modules.proxies.service import ProxyManager, account_proxy

INSIGHTS_SCOPE = "instagram_business_manage_insights"
HOT_INSIGHTS_RECAPTURE_AFTER = timedelta(minutes=5)
ACTIVE_INSIGHTS_RECAPTURE_AFTER = timedelta(minutes=30)
COLD_INSIGHTS_RECAPTURE_AFTER = timedelta(hours=6)
METRICS_BY_PUBLICATION_TYPE = {
    "feed": ("views", "reach", "likes", "comments", "shares", "saved"),
    "reel": ("views", "reach", "likes", "comments", "shares", "saved"),
    "story": ("views", "reach", "shares"),
}


def parse_insights(payload: dict[str, Any]) -> list[tuple[str, float, dict[str, object]]]:
    parsed: list[tuple[str, float, dict[str, object]]] = []
    for item in payload.get("data", []):
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        value: object | None = None
        total_value = item.get("total_value")
        if isinstance(total_value, dict):
            value = total_value.get("value")
        values = item.get("values")
        if value is None and isinstance(values, list) and values and isinstance(values[0], dict):
            value = values[0].get("value")
        if isinstance(value, int | float):
            parsed.append((item["name"], float(value), item))
    return parsed


async def ensure_permission_notice(
    session: AsyncSession,
    *,
    owner_id: uuid.UUID,
    account: Account,
) -> None:
    existing_notice = await session.scalar(
        select(Notification).where(
            Notification.owner_id == owner_id,
            Notification.kind == "insights_permission_required",
            Notification.read_at.is_(None),
        )
    )
    if existing_notice is None:
        session.add(
            Notification(
                owner_id=owner_id,
                kind="insights_permission_required",
                title="Reconecte o Instagram para ativar métricas",
                message=f"@{account.username} precisa autorizar o acesso aos insights.",
                severity="warning",
                data={"account_id": str(account.id)},
            )
        )


async def collect_recent_insights() -> int:
    now = utcnow()
    since = now - timedelta(days=30)
    recent_media = now - timedelta(days=2)
    active_media = now - timedelta(days=7)
    hot_recapture_before = now - HOT_INSIGHTS_RECAPTURE_AFTER
    active_recapture_before = now - ACTIVE_INSIGHTS_RECAPTURE_AFTER
    cold_recapture_before = now - COLD_INSIGHTS_RECAPTURE_AFTER
    async with SessionFactory() as session:
        latest_capture = (
            select(
                InsightSnapshot.external_media_id,
                func.max(InsightSnapshot.captured_at).label("captured_at"),
            )
            .where(InsightSnapshot.external_media_id.is_not(None))
            .group_by(InsightSnapshot.external_media_id)
            .subquery()
        )
        jobs = list(
            (
                await session.execute(
                    select(Job, Campaign.publication_type)
                    .join(Campaign, Campaign.id == Job.campaign_id)
                    .outerjoin(
                        latest_capture,
                        latest_capture.c.external_media_id == Job.external_media_id,
                    )
                    .where(
                        Job.state == "succeeded",
                        Job.published_at >= since,
                        Job.external_media_id.is_not(None),
                        or_(
                            latest_capture.c.captured_at.is_(None),
                            and_(
                                Job.published_at >= recent_media,
                                latest_capture.c.captured_at < hot_recapture_before,
                            ),
                            and_(
                                Job.published_at >= active_media,
                                latest_capture.c.captured_at < active_recapture_before,
                            ),
                            latest_capture.c.captured_at < cold_recapture_before,
                        ),
                    )
                    .order_by(Job.published_at.desc())
                    .limit(500)
                )
            ).all()
        )

    collected = 0
    for job, publication_type in jobs:
        async with SessionFactory() as session:
            account = await session.get(Account, job.account_id)
            setting = await session.scalar(select(Setting).where(Setting.owner_id == job.owner_id))
            token = await session.scalar(
                select(Token)
                .where(Token.account_id == job.account_id, Token.revoked_at.is_(None))
                .order_by(Token.created_at.desc())
            )
            if (
                account is None
                or setting is None
                or token is None
                or not setting.instagram_app_id
                or not setting.instagram_app_secret_ciphertext
                or not job.external_media_id
            ):
                continue
            if INSIGHTS_SCOPE not in account.granted_scopes:
                account.last_error_code = "insights_permission_missing"
                await ensure_permission_notice(
                    session,
                    owner_id=job.owner_id,
                    account=account,
                )
                await session.commit()
                logger.warning(
                    "insights_permission_required",
                    account_id=str(account.id),
                    external_media_id=job.external_media_id,
                )
                continue
            app_secret = secret_box.decrypt(
                setting.instagram_app_secret_ciphertext,
                context=f"instagram-app:{job.owner_id}",
            )
            access_token = secret_box.decrypt(
                token.token_ciphertext,
                context=f"instagram-token:{job.owner_id}:{account.id}",
            )
            try:
                proxy = await account_proxy(session, account_id=account.id, owner_id=job.owner_id)
                async with ProxyManager().create_client(proxy) as http_client:
                    payload = await InstagramClient(
                        app_id=setting.instagram_app_id,
                        app_secret=app_secret,
                        http_client=http_client,
                    ).media_insights(
                        job.external_media_id,
                        access_token,
                        METRICS_BY_PUBLICATION_TYPE.get(
                            publication_type,
                            METRICS_BY_PUBLICATION_TYPE["feed"],
                        ),
                    )
            except InstagramAPIError as exc:
                if exc.error_class == "auth_expired":
                    account.status = "expired"
                elif exc.error_class == "permission_missing":
                    account.last_error_code = "insights_permission_missing"
                    await ensure_permission_notice(
                        session,
                        owner_id=job.owner_id,
                        account=account,
                    )
                logger.warning(
                    "insights_collection_failed",
                    account_id=str(account.id),
                    external_media_id=job.external_media_id,
                    error_class=exc.error_class,
                    response_status=exc.status_code,
                    message=str(exc)[:500],
                )
                await session.commit()
                continue
            metrics = parse_insights(payload)
            account.last_error_code = None
            captured_at = utcnow()
            for metric, value, raw in metrics:
                session.add(
                    InsightSnapshot(
                        owner_id=job.owner_id,
                        account_id=job.account_id,
                        external_media_id=job.external_media_id,
                        metric=metric,
                        value=value,
                        period="lifetime",
                        source_version=settings.INSTAGRAM_API_VERSION,
                        captured_at=captured_at,
                        raw_metadata=raw,
                    )
                )
            await session.commit()
            collected += len(metrics)
            if metrics:
                await publish_user_event(
                    job.owner_id,
                    "insights.updated",
                    {"external_media_id": job.external_media_id},
                )
            else:
                logger.info(
                    "insights_not_available_yet",
                    account_id=str(account.id),
                    external_media_id=job.external_media_id,
                )
    return collected
