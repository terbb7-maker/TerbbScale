import asyncio
import random
import time
import uuid
from collections.abc import Awaitable
from datetime import timedelta
from typing import cast

import httpx
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionFactory
from app.core.logging import logger
from app.core.realtime import publish_user_event
from app.core.redis import get_redis
from app.core.security import secret_box
from app.integrations.instagram import InstagramAPIError, InstagramClient
from app.integrations.storage import StorageClient
from app.models.campaigns import Campaign, CampaignProxy, CampaignProxyAssignment, Job, JobAttempt
from app.models.instagram import Account, Proxy, Setting, Token
from app.models.media import Media
from app.models.operations import CampaignLog, Notification
from app.modules.accounts.health import BLOCKING_HEALTH_STATUSES
from app.modules.common import safe_external_payload, utcnow
from app.modules.proxies.service import (
    ProxyManager,
    campaign_proxy,
    select_account_publication_proxy,
)
from app.workers.account_health import (
    record_account_api_failure,
    record_account_api_success,
)


async def _load_job(
    job_id: uuid.UUID,
) -> tuple[Job, Campaign, Account, Media, Token, Setting] | None:
    async with SessionFactory() as session:
        async with session.begin():
            job = await session.scalar(
                select(Job).where(Job.id == job_id).with_for_update(skip_locked=True)
            )
            if job is None or job.state not in {"queued", "retry_scheduled"}:
                return None
            job.state = "publishing"
            job.attempt_count += 1
            job.lease_owner = f"celery:{job_id}"
            job.lease_expires_at = utcnow() + timedelta(seconds=settings.JOB_LEASE_SECONDS)
        campaign = await session.get(Campaign, job.campaign_id)
        account = await session.get(Account, job.account_id)
        media = await session.get(Media, job.media_id)
        token = await session.scalar(
            select(Token)
            .where(Token.account_id == job.account_id, Token.revoked_at.is_(None))
            .order_by(Token.created_at.desc())
        )
        setting = await session.scalar(select(Setting).where(Setting.owner_id == job.owner_id))
        if not all([campaign, account, media, token, setting]):
            await _fail_permanently(job_id, "missing_dependency", "Recurso da publicação ausente.")
            return None
        return job, campaign, account, media, token, setting


async def _fail_permanently(job_id: uuid.UUID, error_class: str, message: str) -> None:
    async with SessionFactory() as session:
        job = await session.get(Job, job_id)
        if job is None:
            return
        job.state = "failed_permanent"
        job.last_error_class = error_class
        job.last_error_message = message[:1000]
        job.lease_owner = None
        job.lease_expires_at = None
        campaign = await session.get(Campaign, job.campaign_id)
        if campaign:
            campaign.failed_count += 1
            _finish_failed_campaign_if_complete(campaign)
        session.add(
            CampaignLog(
                owner_id=job.owner_id,
                campaign_id=job.campaign_id,
                job_id=job.id,
                account_id=job.account_id,
                media_id=job.media_id,
                event_type="publication_failed",
                status="failed",
                message=message[:1000],
                details={"error_class": error_class},
                occurred_at=utcnow(),
            )
        )
        await session.commit()


async def _publish_job_unlocked(job_id: uuid.UUID) -> None:
    loaded = await _load_job(job_id)
    if loaded is None:
        return
    job, campaign, account, media, token, setting = loaded
    started = time.perf_counter()
    attempt_started = utcnow()
    status_code: int | None = None
    response_payload: dict[str, object] = {}
    error_class: str | None = None
    retryable = False
    proxy_details: dict[str, object] = {"mode": campaign.proxy_mode}
    proxy: Proxy | None = None
    try:
        if campaign.state in {"paused", "cancelled"}:
            await _fail_permanently(job_id, "campaign_inactive", "Campanha pausada ou cancelada.")
            return
        if account.health_status in BLOCKING_HEALTH_STATUSES:
            await _defer_for_account_health(
                job_id,
                account.health_status,
                account.health_action_required or "A conta exige uma ação antes de publicar.",
            )
            return
        if account.status != "connected":
            await _fail_permanently(job_id, "account_ineligible", "Conta não está conectada.")
            return
        if not setting.instagram_app_id or not setting.instagram_app_secret_ciphertext:
            await _fail_permanently(
                job_id, "instagram_app_not_configured", "Instagram App ausente."
            )
            return
        app_secret = secret_box.decrypt(
            setting.instagram_app_secret_ciphertext,
            context=f"instagram-app:{job.owner_id}",
        )
        access_token = secret_box.decrypt(
            token.token_ciphertext,
            context=f"instagram-token:{job.owner_id}:{account.id}",
        )
        proxy, proxy_selection = await _select_publication_proxy(job, campaign, account)
        proxy_details["selection"] = proxy_selection
        if campaign.proxy_mode == "specific" and proxy is None:
            raise InstagramAPIError(
                "proxy_unavailable",
                "O proxy específico da campanha está indisponível.",
                retryable=True,
            )
        if (
            campaign.proxy_mode in {"account", "rotate_per_post", "rotate_every_n_posts"}
            and proxy is None
        ):
            raise InstagramAPIError(
                "proxy_pool_unavailable",
                "A campanha não possui uma proxy saudável disponível no momento.",
                retryable=True,
            )
        if proxy is not None:
            proxy_details.update(
                {
                    "proxy_id": str(proxy.id),
                    "proxy_name": proxy.name,
                    "public_ip": proxy.public_ip,
                    "latency_ms": proxy.latency_ms,
                    "status": proxy.status,
                }
            )
        storage = StorageClient()
        media_url = await storage.signed_url(media.storage_bucket, media.storage_key, 7200)
        cover_url: str | None = None
        if campaign.cover_mode == "custom" and campaign.custom_cover_media_id:
            cover = await _load_owned_media(campaign.custom_cover_media_id, campaign.owner_id)
            if cover is None or cover.media_kind != "image" or cover.status != "ready":
                await _fail_permanently(
                    job_id,
                    "invalid_custom_cover",
                    "A capa personalizada não está disponível.",
                )
                return
            cover_url = await storage.signed_url(
                cover.storage_bucket,
                cover.thumbnail_key or cover.storage_key,
                7200,
            )
        caption = campaign.caption or ""
        if campaign.hashtags:
            caption = f"{caption}\n\n" + " ".join(f"#{tag}" for tag in campaign.hashtags)
        if job.external_container_id is None:
            if campaign.publication_type == "story":
                media_type = "STORIES"
            elif media.media_kind == "video":
                media_type = "REELS"
            else:
                media_type = "IMAGE"
            async with ProxyManager().create_client(proxy) as http_client:
                container_id = await InstagramClient(
                    app_id=setting.instagram_app_id, app_secret=app_secret, http_client=http_client
                ).create_container(
                    account_id=account.instagram_user_id,
                    token=access_token,
                    media_url=media_url,
                    media_type=media_type,
                    is_image=media.media_kind == "image",
                    caption=caption or None,
                    cover_url=cover_url,
                )
            async with SessionFactory() as session:
                current = await session.get(Job, job_id)
                if current:
                    current.external_container_id = container_id
                    await session.commit()
            job.external_container_id = container_id

        if media.media_kind == "video":
            for _ in range(30):
                async with ProxyManager().create_client(proxy) as http_client:
                    container_status = await InstagramClient(
                        app_id=setting.instagram_app_id,
                        app_secret=app_secret,
                        http_client=http_client,
                    ).container_status(job.external_container_id, access_token)
                if container_status == "FINISHED":
                    break
                if container_status in {"ERROR", "EXPIRED"}:
                    raise InstagramAPIError(
                        "container_failed",
                        f"Container terminou com status {container_status}",
                        retryable=False,
                    )
                await asyncio.sleep(5)
            else:
                raise InstagramAPIError(
                    "container_processing",
                    "Container ainda está processando.",
                    retryable=True,
                )

        async with ProxyManager().create_client(proxy) as http_client:
            external_media_id = await InstagramClient(
                app_id=setting.instagram_app_id, app_secret=app_secret, http_client=http_client
            ).publish(
                account_id=account.instagram_user_id,
                container_id=job.external_container_id,
                token=access_token,
            )
        response_payload = {"external_media_id": external_media_id, "proxy": proxy_details}
        now = utcnow()
        async with SessionFactory() as session:
            current = await session.get(Job, job_id)
            current_account = await session.get(Account, account.id)
            current_campaign = await session.get(Campaign, campaign.id)
            if current is None or current.state == "succeeded":
                return
            current.state = "succeeded"
            current.external_media_id = external_media_id
            current.published_at = now
            current.lease_owner = None
            current.lease_expires_at = None
            if current_account:
                current_account.published_count += 1
                current_account.last_published_at = now
            if current_campaign:
                current_campaign.succeeded_count += 1
                if (
                    current_campaign.succeeded_count + current_campaign.failed_count
                    >= current_campaign.planned_count
                ):
                    current_campaign.state = (
                        "completed_with_errors" if current_campaign.failed_count else "completed"
                    )
                    current_campaign.completed_at = now
                    session.add(
                        Notification(
                            owner_id=current.owner_id,
                            kind="campaign_completed",
                            title="Campanha finalizada",
                            message=f"{current_campaign.name} terminou.",
                            severity="success" if not current_campaign.failed_count else "warning",
                            data={"campaign_id": str(current_campaign.id)},
                        )
                    )
            session.add(
                CampaignLog(
                    owner_id=current.owner_id,
                    campaign_id=current.campaign_id,
                    job_id=current.id,
                    account_id=current.account_id,
                    media_id=current.media_id,
                    event_type="publication_succeeded",
                    status="succeeded",
                    message="Publicação concluída.",
                    details=response_payload,
                    occurred_at=now,
                    duration_ms=round((time.perf_counter() - started) * 1000),
                )
            )
            await session.commit()
        await publish_user_event(
            job.owner_id,
            "publication.succeeded",
            {"job_id": str(job.id), "campaign_id": str(campaign.id)},
        )
        try:
            await record_account_api_success(account.id, source="publication")
        except Exception as exc:
            logger.warning(
                "account_health_success_record_failed",
                account_id=str(account.id),
                error_type=type(exc).__name__,
            )
    except InstagramAPIError as exc:
        error_class = exc.error_class
        retryable = exc.retryable
        status_code = exc.status_code
        response_payload = exc.payload
        try:
            await record_account_api_failure(account.id, exc, source="publication")
        except Exception as health_exc:
            logger.warning(
                "account_health_failure_record_failed",
                account_id=str(account.id),
                error_type=type(health_exc).__name__,
            )
        await _handle_failure(
            job_id,
            exc.error_class,
            str(exc),
            retryable,
            response_status=status_code,
            provider_response={**response_payload, "proxy": proxy_details},
        )
    except httpx.HTTPError as exc:
        error_class = "proxy_transport_failure" if proxy is not None else "temporary_network_error"
        retryable = True
        if proxy is not None:
            await _mark_proxy_transport_failure(proxy.id)
            proxy_details["cooldown_applied"] = True
        response_payload = {"exception_type": type(exc).__name__}
        await _handle_failure(
            job_id,
            error_class,
            "Não foi possível conectar pela proxy da publicação. "
            "O sistema tentará outra proxy saudável.",
            retryable,
            provider_response={**response_payload, "proxy": proxy_details},
        )
    except Exception as exc:
        error_class = "temporary_internal_error"
        retryable = True
        response_payload = {"message": str(exc)[:1000]}
        await _handle_failure(
            job_id,
            error_class,
            str(exc),
            retryable,
            provider_response={**response_payload, "proxy": proxy_details},
        )
    finally:
        async with SessionFactory() as session:
            current = await session.get(Job, job_id)
            if current:
                session.add(
                    JobAttempt(
                        owner_id=current.owner_id,
                        job_id=current.id,
                        attempt_number=current.attempt_count,
                        started_at=attempt_started,
                        finished_at=utcnow(),
                        duration_ms=round((time.perf_counter() - started) * 1000),
                        request_operation="publish",
                        response_status=status_code,
                        sanitized_response=safe_external_payload(response_payload),
                        error_class=error_class,
                        retryable=retryable,
                        proxy_id=current.proxy_id,
                    )
                )
                await session.commit()


async def publish_job(job_id: uuid.UUID) -> bool:
    """Publish one job while preserving the planned order for its account."""
    async with SessionFactory() as session:
        job = await session.get(Job, job_id)
        if job is None or job.state not in {"queued", "retry_scheduled"}:
            return True
        account_id = job.account_id
        campaign_version_id = job.campaign_version_id
        plan_position = job.plan_position

    redis = get_redis()
    lock_key = f"publication-account-lock:{account_id}"
    lock_token = uuid.uuid4().hex
    try:
        acquired = await redis.set(
            lock_key,
            lock_token,
            ex=settings.JOB_LEASE_SECONDS + 60,
            nx=True,
        )
    except Exception as exc:
        logger.warning(
            "publication_account_lock_unavailable",
            account_id=str(account_id),
            error_type=type(exc).__name__,
        )
        return False
    if not acquired:
        return False

    try:
        async with SessionFactory() as session:
            predecessor = await session.scalar(
                select(Job.id)
                .where(
                    Job.campaign_version_id == campaign_version_id,
                    Job.account_id == account_id,
                    Job.plan_position < plan_position,
                    Job.state.notin_(
                        {"succeeded", "dead_letter", "failed_permanent", "cancelled"}
                    ),
                )
                .limit(1)
            )
        if predecessor is not None:
            return False
        await _publish_job_unlocked(job_id)
        return True
    finally:
        try:
            await cast(
                Awaitable[object],
                redis.eval(
                    """
                    if redis.call('get', KEYS[1]) == ARGV[1] then
                      return redis.call('del', KEYS[1])
                    end
                    return 0
                    """,
                    1,
                    lock_key,
                    lock_token,
                ),
            )
        except Exception as exc:
            logger.warning(
                "publication_account_lock_release_failed",
                account_id=str(account_id),
                error_type=type(exc).__name__,
            )


async def _select_publication_proxy(
    job: Job, campaign: Campaign, account: Account
) -> tuple[Proxy | None, str]:
    if campaign.proxy_mode == "none":
        return None, "direct"
    if campaign.proxy_mode in {"specific", "fixed"}:
        async with SessionFactory() as session:
            return await campaign_proxy(
                session, campaign=campaign, account=account
            ), "campaign_fixed"

    if campaign.proxy_mode in {"rotate_per_post", "rotate_every_n_posts"}:
        async with SessionFactory() as session:
            async with session.begin():
                locked_campaign = await session.scalar(
                    select(Campaign).where(Campaign.id == campaign.id).with_for_update()
                )
                if locked_campaign is None:
                    return None, "campaign_not_found"
                assignment = await session.get(
                    CampaignProxyAssignment,
                    (job.campaign_version_id, job.rotation_slot),
                )
                assigned_proxy = (
                    await session.get(Proxy, assignment.proxy_id) if assignment else None
                )
                now = utcnow()
                if (
                    assigned_proxy
                    and assigned_proxy.is_active
                    and assigned_proxy.status == "online"
                    and (
                        assigned_proxy.cooldown_until is None
                        or assigned_proxy.cooldown_until <= now
                    )
                ):
                    job.proxy_id = assigned_proxy.id
                    current = await session.get(Job, job.id)
                    if current:
                        current.proxy_id = assigned_proxy.id
                    return assigned_proxy, "campaign_round_assignment"
                rows = (
                    await session.execute(
                        select(CampaignProxy, Proxy)
                        .join(Proxy, Proxy.id == CampaignProxy.proxy_id)
                        .where(
                            CampaignProxy.campaign_id == campaign.id,
                            Proxy.is_active.is_(True),
                            Proxy.status == "online",
                        )
                        .order_by(CampaignProxy.priority)
                    )
                ).all()
                rows = [
                    row
                    for row in rows
                    if row[1].cooldown_until is None or row[1].cooldown_until <= now
                ]
                if not rows:
                    return None, "campaign_pool_unavailable"
                rotation_index = job.rotation_slot
                if campaign.proxy_mode == "rotate_every_n_posts":
                    rotation_index //= campaign.proxy_rotation_every
                selected_proxy = rows[rotation_index % len(rows)][1]
                if assignment is None:
                    session.add(
                        CampaignProxyAssignment(
                            campaign_version_id=job.campaign_version_id,
                            rotation_slot=job.rotation_slot,
                            proxy_id=selected_proxy.id,
                            selected_at=now,
                        )
                    )
                else:
                    assignment.proxy_id = selected_proxy.id
                    assignment.selected_at = now
                current = await session.get(Job, job.id)
                if current:
                    current.proxy_id = selected_proxy.id
                job.proxy_id = selected_proxy.id
                return selected_proxy, "campaign_rotation"

    async with SessionFactory() as session:
        async with session.begin():
            current = await session.get(Job, job.id)
            retry_after_transport_failure = (
                current is not None and current.last_error_class == "proxy_transport_failure"
            )
            proxy, reason = await select_account_publication_proxy(
                session,
                account_id=account.id,
                owner_id=job.owner_id,
                exclude_proxy_id=current.proxy_id
                if current and retry_after_transport_failure
                else None,
            )
            if proxy is not None and current is not None:
                current.proxy_id = proxy.id
                job.proxy_id = proxy.id
        return proxy, reason


async def _mark_proxy_transport_failure(proxy_id: uuid.UUID) -> None:
    async with SessionFactory() as session:
        proxy = await session.get(Proxy, proxy_id)
        if proxy is None:
            return
        ProxyManager().apply_transport_failure(proxy)
        await session.commit()


async def _load_owned_media(media_id: uuid.UUID, owner_id: uuid.UUID) -> Media | None:
    async with SessionFactory() as session:
        return await session.scalar(
            select(Media).where(
                Media.id == media_id,
                Media.owner_id == owner_id,
                Media.deleted_at.is_(None),
            )
        )


async def _handle_failure(
    job_id: uuid.UUID,
    error_class: str,
    message: str,
    retryable: bool,
    *,
    response_status: int | None = None,
    provider_response: dict[str, object] | None = None,
) -> None:
    async with SessionFactory() as session:
        job = await session.get(Job, job_id)
        if job is None:
            return
        now = utcnow()
        has_budget = retryable and job.attempt_count < settings.MAX_PUBLICATION_ATTEMPTS
        job.state = "retry_scheduled" if has_budget else "dead_letter"
        job.last_error_class = error_class
        job.last_error_message = message[:1000]
        job.lease_owner = None
        job.lease_expires_at = None
        if has_budget:
            delay = min(30 * (2 ** max(job.attempt_count - 1, 0)), 3600)
            job.next_attempt_at = now + timedelta(seconds=delay + random.randint(0, 15))
        else:
            campaign = await session.get(Campaign, job.campaign_id)
            if campaign:
                campaign.failed_count += 1
                _finish_failed_campaign_if_complete(campaign)
            session.add(
                Notification(
                    owner_id=job.owner_id,
                    kind="publication_failed",
                    title="Publicação com falha",
                    message=message[:500],
                    severity="error",
                    data={"job_id": str(job.id), "campaign_id": str(job.campaign_id)},
                )
            )
        session.add(
            CampaignLog(
                owner_id=job.owner_id,
                campaign_id=job.campaign_id,
                job_id=job.id,
                account_id=job.account_id,
                media_id=job.media_id,
                event_type="publication_retry" if has_budget else "publication_dead_letter",
                status=job.state,
                message=message[:1000],
                details={
                    "error_class": error_class,
                    "retryable": retryable,
                    "response_status": response_status,
                    "provider_response": safe_external_payload(provider_response or {}),
                },
                occurred_at=now,
            )
        )
        await session.commit()
    await publish_user_event(
        job.owner_id,
        "publication.failed",
        {"job_id": str(job.id), "state": job.state, "error_class": error_class},
    )


def _finish_failed_campaign_if_complete(campaign: Campaign) -> None:
    if campaign.succeeded_count + campaign.failed_count < campaign.planned_count:
        return
    campaign.state = "completed_with_errors"
    campaign.completed_at = utcnow()


async def _defer_for_account_health(
    job_id: uuid.UUID,
    health_status: str,
    message: str,
) -> None:
    async with SessionFactory() as session:
        job = await session.get(Job, job_id)
        if job is None:
            return
        now = utcnow()
        job.state = "retry_scheduled"
        job.next_attempt_at = now + timedelta(minutes=15)
        job.attempt_count = max(0, job.attempt_count - 1)
        job.lease_owner = None
        job.lease_expires_at = None
        job.last_error_class = "account_health_blocked"
        job.last_error_message = message[:1000]
        session.add(
            CampaignLog(
                owner_id=job.owner_id,
                campaign_id=job.campaign_id,
                job_id=job.id,
                account_id=job.account_id,
                media_id=job.media_id,
                event_type="publication_deferred_account_health",
                status="retry_scheduled",
                message=message[:1000],
                details={"health_status": health_status},
                occurred_at=now,
            )
        )
        await session.commit()


async def record_worker_runtime_failure(job_id: uuid.UUID, exc: Exception) -> None:
    """Persist failures that happen outside the publication pipeline itself."""
    async with SessionFactory() as session:
        async with session.begin():
            job = await session.scalar(
                select(Job).where(Job.id == job_id).with_for_update(skip_locked=True)
            )
            if job is None or job.state in {
                "succeeded",
                "dead_letter",
                "failed_permanent",
                "cancelled",
            }:
                return
            if job.state != "publishing":
                job.attempt_count += 1
            now = utcnow()
            has_budget = job.attempt_count < settings.MAX_PUBLICATION_ATTEMPTS
            job.state = "retry_scheduled" if has_budget else "dead_letter"
            job.next_attempt_at = now + timedelta(seconds=45) if has_budget else None
            job.lease_owner = None
            job.lease_expires_at = None
            job.last_error_class = "worker_runtime_error"
            job.last_error_message = f"{type(exc).__name__}: {str(exc)[:900]}"
            if not has_budget:
                campaign = await session.get(Campaign, job.campaign_id)
                if campaign:
                    campaign.failed_count += 1
                    _finish_failed_campaign_if_complete(campaign)
            details = safe_external_payload(
                {
                    "error_class": "worker_runtime_error",
                    "exception_type": type(exc).__name__,
                    "message": str(exc)[:1000],
                    "retryable": has_budget,
                }
            )
            session.add(
                CampaignLog(
                    owner_id=job.owner_id,
                    campaign_id=job.campaign_id,
                    job_id=job.id,
                    account_id=job.account_id,
                    media_id=job.media_id,
                    event_type="worker_retry" if has_budget else "worker_dead_letter",
                    status=job.state,
                    message="O worker encontrou uma falha interna antes de publicar.",
                    details=details,
                    occurred_at=now,
                )
            )
            session.add(
                JobAttempt(
                    owner_id=job.owner_id,
                    job_id=job.id,
                    attempt_number=job.attempt_count,
                    started_at=now,
                    finished_at=now,
                    duration_ms=0,
                    request_operation="worker_runtime",
                    sanitized_response=details,
                    error_class="worker_runtime_error",
                    retryable=has_budget,
                    proxy_id=job.proxy_id,
                )
            )
