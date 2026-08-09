import uuid
from collections import defaultdict
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import func, select, update

from app.core.config import settings
from app.core.errors import AppError
from app.models.campaigns import (
    Campaign,
    CampaignAccount,
    CampaignMedia,
    Job,
    JobAttempt,
)
from app.models.instagram import Account, Proxy
from app.models.media import Media
from app.models.operations import CampaignLog, SchedulerState
from app.modules.auth.dependencies import ActiveUserDep, SessionDep
from app.modules.campaigns.schemas import (
    CampaignAccountDetail,
    CampaignDetail,
    CampaignEventDetail,
    CampaignInput,
    CampaignJobAttemptDetail,
    CampaignJobDetail,
    CampaignMediaDetail,
    CampaignOut,
    CampaignPreview,
    CampaignQueueSummary,
    CampaignSchedulerDetail,
)
from app.modules.campaigns.service import (
    activate_campaign,
    apply_campaign_input,
    preview_campaign,
)
from app.modules.common import utcnow

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


async def owned_campaign(
    campaign_id: uuid.UUID,
    owner_id: uuid.UUID,
    session: SessionDep,
) -> Campaign:
    campaign = await session.scalar(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.owner_id == owner_id)
    )
    if campaign is None:
        raise AppError("campaign_not_found", "Campanha não encontrada.", status_code=404)
    return campaign


@router.get("", response_model=list[CampaignOut])
async def list_campaigns(user: ActiveUserDep, session: SessionDep) -> list[Campaign]:
    query = (
        select(Campaign)
        .where(Campaign.owner_id == user.id)
        .order_by(Campaign.created_at.desc())
        .limit(200)
    )
    return list((await session.scalars(query)).all())


@router.post("", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignInput,
    user: ActiveUserDep,
    session: SessionDep,
) -> Campaign:
    campaign = Campaign(
        owner_id=user.id,
        name=payload.name,
        publication_type=payload.publication_type,
        media_strategy=payload.media_strategy,
        posts_per_hour=payload.posts_per_hour,
        duration_hours=payload.duration_hours,
        schedule_distribution=payload.schedule_distribution,
        post_cooldown_minutes=payload.post_cooldown_minutes,
        schedule_mode=payload.schedule_mode,
        timezone=payload.timezone,
        proxy_mode=payload.proxy_mode,
        proxy_id=payload.proxy_id,
        proxy_rotation_every=payload.proxy_rotation_every,
        state="draft",
    )
    session.add(campaign)
    await session.flush()
    await apply_campaign_input(campaign, payload, session)
    await session.commit()
    await session.refresh(campaign)
    return campaign


@router.post("/preview", response_model=CampaignPreview)
async def preview(
    payload: CampaignInput,
    user: ActiveUserDep,
    session: SessionDep,
) -> CampaignPreview:
    result, _ = await preview_campaign(payload, user.id, session)
    return result


@router.get("/{campaign_id}", response_model=CampaignDetail)
async def campaign_detail(
    campaign_id: uuid.UUID,
    user: ActiveUserDep,
    session: SessionDep,
    job_limit: Annotated[int, Query(ge=1, le=1000)] = 250,
    event_limit: Annotated[int, Query(ge=1, le=1000)] = 250,
) -> CampaignDetail:
    campaign = await owned_campaign(campaign_id, user.id, session)
    account_rows = (
        (
            await session.execute(
                select(
                    CampaignAccount.position,
                    Account.id,
                    Account.username,
                    Account.display_name,
                    Account.profile_picture_url,
                    Account.status,
                    Account.token_expires_at,
                    Account.published_count,
                    Account.last_published_at,
                )
                .join(Account, Account.id == CampaignAccount.account_id)
                .where(
                    CampaignAccount.campaign_id == campaign.id,
                    Account.owner_id == user.id,
                )
                .order_by(CampaignAccount.position)
            )
        )
        .mappings()
        .all()
    )
    account_state_rows = (
        await session.execute(
            select(Job.account_id, Job.state, func.count(Job.id).label("total"))
            .where(Job.campaign_id == campaign.id, Job.owner_id == user.id)
            .group_by(Job.account_id, Job.state)
        )
    ).all()
    account_job_counts: dict[uuid.UUID, dict[str, int]] = defaultdict(dict)
    for account_id, state, total in account_state_rows:
        account_job_counts[account_id][state] = int(total)
    accounts = [
        CampaignAccountDetail(
            **dict(row),
            job_counts=account_job_counts.get(row["id"], {}),
        )
        for row in account_rows
    ]

    media_rows = (
        (
            await session.execute(
                select(
                    CampaignMedia.position,
                    Media.id,
                    Media.display_name,
                    Media.media_kind,
                    Media.mime_type,
                    Media.size_bytes,
                    Media.duration_ms,
                    Media.width,
                    Media.height,
                    Media.status,
                    Media.failure_reason,
                )
                .join(Media, Media.id == CampaignMedia.media_id)
                .where(
                    CampaignMedia.campaign_id == campaign.id,
                    Media.owner_id == user.id,
                )
                .order_by(CampaignMedia.position)
            )
        )
        .mappings()
        .all()
    )
    campaign_media = [CampaignMediaDetail(**dict(row)) for row in media_rows]

    state_rows = (
        await session.execute(
            select(Job.state, func.count(Job.id))
            .where(Job.campaign_id == campaign.id, Job.owner_id == user.id)
            .group_by(Job.state)
        )
    ).all()
    state_counts = {state: int(total) for state, total in state_rows}
    total_jobs = sum(state_counts.values())
    finished_states = {"succeeded", "dead_letter", "failed_permanent", "cancelled"}
    active_states = {"planned", "queued", "publishing", "retry_scheduled"}
    finished_jobs = sum(state_counts.get(item, 0) for item in finished_states)
    active_jobs = sum(state_counts.get(item, 0) for item in active_states)
    queue = CampaignQueueSummary(
        total=total_jobs,
        active=active_jobs,
        finished=finished_jobs,
        progress_percent=round((finished_jobs / total_jobs) * 100) if total_jobs else 0,
        counts=state_counts,
    )

    job_rows = (
        (
            await session.execute(
                select(
                    Job.id,
                    Job.state,
                    Job.priority,
                    Job.plan_position,
                    Job.rotation_slot,
                    Job.scheduled_at,
                    Job.attempt_count,
                    Job.next_attempt_at,
                    Job.lease_expires_at,
                    Job.published_at,
                    Job.external_container_id,
                    Job.external_media_id,
                    Job.last_error_class,
                    Job.last_error_message,
                    Account.id.label("account_id"),
                    Account.username.label("account_username"),
                    Media.id.label("media_id"),
                    Media.display_name.label("media_name"),
                    Proxy.id.label("proxy_id"),
                    Proxy.name.label("proxy_name"),
                )
                .join(Account, Account.id == Job.account_id)
                .join(Media, Media.id == Job.media_id)
                .outerjoin(Proxy, Proxy.id == Job.proxy_id)
                .where(Job.campaign_id == campaign.id, Job.owner_id == user.id)
                .order_by(Job.scheduled_at, Job.plan_position, Job.id)
                .limit(job_limit + 1)
            )
        )
        .mappings()
        .all()
    )
    jobs_truncated = len(job_rows) > job_limit
    visible_job_rows = job_rows[:job_limit]
    visible_job_ids = [row["id"] for row in visible_job_rows]
    attempts_by_job: dict[uuid.UUID, list[CampaignJobAttemptDetail]] = defaultdict(list)
    if visible_job_ids:
        attempt_rows = (
            (
                await session.execute(
                    select(
                        JobAttempt.id,
                        JobAttempt.job_id,
                        JobAttempt.attempt_number,
                        JobAttempt.started_at,
                        JobAttempt.finished_at,
                        JobAttempt.duration_ms,
                        JobAttempt.request_operation,
                        JobAttempt.response_status,
                        JobAttempt.external_trace_id,
                        JobAttempt.sanitized_response,
                        JobAttempt.error_class,
                        JobAttempt.retryable,
                        JobAttempt.proxy_id,
                    )
                    .where(
                        JobAttempt.owner_id == user.id,
                        JobAttempt.job_id.in_(visible_job_ids),
                    )
                    .order_by(JobAttempt.job_id, JobAttempt.attempt_number)
                )
            )
            .mappings()
            .all()
        )
        for row in attempt_rows:
            attempt_data = dict(row)
            job_id = attempt_data.pop("job_id")
            attempts_by_job[job_id].append(CampaignJobAttemptDetail(**attempt_data))
    jobs = [
        CampaignJobDetail(
            **dict(row),
            attempts=attempts_by_job.get(row["id"], []),
        )
        for row in visible_job_rows
    ]

    event_rows = (
        (
            await session.execute(
                select(
                    CampaignLog.id,
                    CampaignLog.job_id,
                    CampaignLog.event_type,
                    CampaignLog.status,
                    CampaignLog.message,
                    CampaignLog.details,
                    CampaignLog.occurred_at,
                    CampaignLog.duration_ms,
                    Account.username.label("account_username"),
                    Media.display_name.label("media_name"),
                )
                .outerjoin(Account, Account.id == CampaignLog.account_id)
                .outerjoin(Media, Media.id == CampaignLog.media_id)
                .where(
                    CampaignLog.campaign_id == campaign.id,
                    CampaignLog.owner_id == user.id,
                )
                .order_by(CampaignLog.occurred_at.desc(), CampaignLog.id.desc())
                .limit(event_limit + 1)
            )
        )
        .mappings()
        .all()
    )
    events_truncated = len(event_rows) > event_limit
    events = [CampaignEventDetail(**dict(row)) for row in event_rows[:event_limit]]

    scheduler_row = await session.get(SchedulerState, "publication-dispatcher")
    scheduler_detail: CampaignSchedulerDetail | None = None
    if scheduler_row is not None:
        recent = bool(
            scheduler_row.last_success_at
            and scheduler_row.last_success_at >= utcnow() - timedelta(minutes=3)
        )
        scheduler_detail = CampaignSchedulerDetail(
            status="operational" if recent and not scheduler_row.last_error else "degraded",
            last_success_at=scheduler_row.last_success_at,
            last_error=scheduler_row.last_error,
            metadata=scheduler_row.metadata_json,
        )

    return CampaignDetail(
        **CampaignOut.model_validate(campaign).model_dump(),
        account_ids=[item.id for item in accounts],
        media_ids=[item.id for item in campaign_media],
        accounts=accounts,
        media=campaign_media,
        queue=queue,
        jobs=jobs,
        jobs_truncated=jobs_truncated,
        events=events,
        events_truncated=events_truncated,
        scheduler=scheduler_detail,
        max_attempts=settings.MAX_PUBLICATION_ATTEMPTS,
    )


@router.patch("/{campaign_id}", response_model=CampaignOut)
async def edit_campaign(
    campaign_id: uuid.UUID,
    payload: CampaignInput,
    user: ActiveUserDep,
    session: SessionDep,
) -> Campaign:
    campaign = await owned_campaign(campaign_id, user.id, session)
    if campaign.state != "draft":
        raise AppError(
            "campaign_state_conflict", "Somente rascunhos podem ser editados.", status_code=409
        )
    await apply_campaign_input(campaign, payload, session)
    await session.commit()
    return campaign


@router.post("/{campaign_id}/activate", response_model=CampaignPreview)
async def activate(
    campaign_id: uuid.UUID,
    payload: CampaignInput,
    user: ActiveUserDep,
    session: SessionDep,
) -> CampaignPreview:
    campaign = await owned_campaign(campaign_id, user.id, session)
    return await activate_campaign(campaign, payload, user.id, session)


@router.post("/{campaign_id}/duplicate", response_model=CampaignOut)
async def duplicate_campaign(
    campaign_id: uuid.UUID,
    user: ActiveUserDep,
    session: SessionDep,
) -> Campaign:
    source = await owned_campaign(campaign_id, user.id, session)
    accounts = list(
        (
            await session.scalars(
                select(CampaignAccount)
                .where(CampaignAccount.campaign_id == source.id)
                .order_by(CampaignAccount.position)
            )
        ).all()
    )
    media = list(
        (
            await session.scalars(
                select(CampaignMedia)
                .where(CampaignMedia.campaign_id == source.id)
                .order_by(CampaignMedia.position)
            )
        ).all()
    )
    clone = Campaign(
        owner_id=user.id,
        name=f"{source.name} — cópia",
        description=source.description,
        caption=source.caption,
        hashtags=source.hashtags,
        publication_type=source.publication_type,
        media_strategy=source.media_strategy,
        posts_per_hour=source.posts_per_hour,
        duration_hours=source.duration_hours,
        schedule_mode=source.schedule_mode,
        starts_at=None,
        timezone=source.timezone,
        cover_mode=source.cover_mode,
        proxy_mode=source.proxy_mode,
        proxy_id=source.proxy_id,
        custom_cover_media_id=source.custom_cover_media_id,
        allow_media_reuse=source.allow_media_reuse,
        state="draft",
    )
    session.add(clone)
    await session.flush()
    for account_link in accounts:
        session.add(
            CampaignAccount(
                campaign_id=clone.id,
                account_id=account_link.account_id,
                position=account_link.position,
                snapshot=account_link.snapshot,
            )
        )
    for media_link in media:
        session.add(
            CampaignMedia(
                campaign_id=clone.id,
                media_id=media_link.media_id,
                position=media_link.position,
                snapshot=media_link.snapshot,
            )
        )
    await session.commit()
    return clone


@router.post("/{campaign_id}/pause", response_model=CampaignOut)
async def pause_campaign(
    campaign_id: uuid.UUID,
    user: ActiveUserDep,
    session: SessionDep,
) -> Campaign:
    campaign = await owned_campaign(campaign_id, user.id, session)
    if campaign.state not in {"scheduled", "running"}:
        raise AppError(
            "campaign_state_conflict", "A campanha não pode ser pausada.", status_code=409
        )
    campaign.state = "paused"
    campaign.paused_at = utcnow()
    await session.commit()
    return campaign


@router.post("/{campaign_id}/resume", response_model=CampaignOut)
async def resume_campaign(
    campaign_id: uuid.UUID,
    user: ActiveUserDep,
    session: SessionDep,
) -> Campaign:
    campaign = await owned_campaign(campaign_id, user.id, session)
    if campaign.state != "paused":
        raise AppError("campaign_state_conflict", "A campanha não está pausada.", status_code=409)
    campaign.state = "scheduled"
    campaign.paused_at = None
    await session.commit()
    return campaign


@router.post("/{campaign_id}/cancel", response_model=CampaignOut)
async def cancel_campaign(
    campaign_id: uuid.UUID,
    user: ActiveUserDep,
    session: SessionDep,
) -> Campaign:
    campaign = await owned_campaign(campaign_id, user.id, session)
    if campaign.state in {"completed", "cancelled"}:
        raise AppError("campaign_state_conflict", "A campanha já terminou.", status_code=409)
    now = utcnow()
    campaign.state = "cancelled"
    campaign.cancelled_at = now
    await session.execute(
        update(Job)
        .where(
            Job.campaign_id == campaign.id,
            Job.state.in_(["planned", "queued", "retry_scheduled"]),
        )
        .values(state="cancelled", updated_at=now)
    )
    await session.commit()
    return campaign
