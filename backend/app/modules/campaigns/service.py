import hashlib
import random
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.campaigns import (
    Campaign,
    CampaignAccount,
    CampaignMedia,
    CampaignProxy,
    CampaignVersion,
    Job,
)
from app.models.instagram import Account, Proxy
from app.models.media import Media
from app.modules.accounts.health import BLOCKING_HEALTH_STATUSES
from app.modules.campaigns.schemas import CampaignInput, CampaignPreview, PlanItem
from app.modules.common import utcnow


@dataclass(frozen=True, slots=True)
class PlanningContext:
    accounts: list[Account]
    media: list[Media]
    starts_at: datetime
    seed: str


async def load_context(
    payload: CampaignInput,
    owner_id: uuid.UUID,
    session: AsyncSession,
) -> tuple[PlanningContext | None, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    account_rows = list(
        (
            await session.scalars(
                select(Account).where(
                    Account.owner_id == owner_id,
                    Account.id.in_(payload.account_ids),
                    Account.removed_at.is_(None),
                )
            )
        ).all()
    )
    accounts_by_id = {item.id: item for item in account_rows}
    accounts = [
        accounts_by_id[item_id] for item_id in payload.account_ids if item_id in accounts_by_id
    ]
    if len(accounts) != len(set(payload.account_ids)):
        errors.append("Uma ou mais contas não existem ou não pertencem ao usuário.")
    disconnected = [
        item.username
        for item in accounts
        if item.status != "connected" and item.health_status not in BLOCKING_HEALTH_STATUSES
    ]
    if disconnected:
        errors.append(f"Contas indisponíveis: {', '.join(disconnected[:5])}.")
    health_blocked = [
        item.username for item in accounts if item.health_status in BLOCKING_HEALTH_STATUSES
    ]
    if health_blocked:
        errors.append(
            "Contas com ação necessária no Instagram: "
            f"{', '.join(health_blocked[:5])}."
        )

    media_rows = list(
        (
            await session.scalars(
                select(Media).where(
                    Media.owner_id == owner_id,
                    Media.id.in_(payload.media_ids),
                    Media.deleted_at.is_(None),
                )
            )
        ).all()
    )
    media_by_id = {item.id: item for item in media_rows}
    media = [media_by_id[item_id] for item_id in payload.media_ids if item_id in media_by_id]
    if len(media) != len(set(payload.media_ids)):
        errors.append("Uma ou mais mídias não existem ou não pertencem ao usuário.")
    not_ready = [item.display_name for item in media if item.status != "ready"]
    if not_ready:
        errors.append(f"Mídias ainda não estão prontas: {', '.join(not_ready[:5])}.")
    if payload.publication_type == "reel":
        non_video = [item.display_name for item in media if item.media_kind != "video"]
        if non_video:
            errors.append(f"Reels exigem vídeos: {', '.join(non_video[:5])}.")

    if payload.cover_mode == "custom" and payload.custom_cover_media_id:
        cover = await session.scalar(
            select(Media).where(
                Media.id == payload.custom_cover_media_id,
                Media.owner_id == owner_id,
                Media.deleted_at.is_(None),
            )
        )
        if cover is None:
            errors.append("A capa personalizada não existe ou não pertence ao usuário.")
        elif cover.media_kind != "image":
            errors.append("A capa personalizada precisa ser uma imagem.")
        elif cover.status != "ready":
            errors.append("A capa personalizada ainda está sendo processada.")

    if payload.proxy_mode == "fixed" and payload.proxy_id:
        proxy = await session.scalar(
            select(Proxy).where(Proxy.id == payload.proxy_id, Proxy.owner_id == owner_id)
        )
        if proxy is None:
            errors.append("O proxy selecionado não existe ou não pertence ao usuário.")
        elif not proxy.is_active:
            errors.append("O proxy selecionado está inativo.")
    if payload.proxy_mode.startswith("rotate_"):
        proxies = list(
            (
                await session.scalars(
                    select(Proxy).where(
                        Proxy.id.in_(payload.proxy_ids),
                        Proxy.owner_id == owner_id,
                        Proxy.is_active.is_(True),
                    )
                )
            ).all()
        )
        if len(proxies) != len(set(payload.proxy_ids)):
            errors.append(
                "Uma ou mais proxies do pool não existem, não pertencem ao usuário "
                "ou estão inativas."
            )

    try:
        ZoneInfo(payload.timezone)
    except ZoneInfoNotFoundError:
        errors.append("Timezone inválido.")

    starts_at = payload.starts_at or utcnow()
    if starts_at.tzinfo is None:
        errors.append("starts_at precisa incluir timezone.")
        starts_at = starts_at.replace(tzinfo=UTC)
    if starts_at < utcnow() - timedelta(minutes=1):
        errors.append("A data da campanha está no passado.")

    requested_per_account = payload.posts_per_hour * payload.duration_hours
    if (
        not payload.allow_media_reuse
        and payload.media_strategy != "same_media"
        and requested_per_account > len(media)
    ):
        warnings.append(
            "Cada conta receberá no máximo uma publicação por mídia selecionada."
        )
    if payload.media_strategy == "same_media" and len(media) > 1:
        warnings.append(
            "Na estratégia mesma mídia, apenas a primeira mídia selecionada será usada."
        )
    if payload.publication_type == "story" and payload.caption:
        warnings.append("A legenda poderá ser ignorada pelo Instagram em Stories.")

    if errors:
        return None, errors, warnings
    return (
        PlanningContext(
            accounts,
            media,
            starts_at.astimezone(UTC),
            payload.planning_seed or uuid.uuid4().hex,
        ),
        errors,
        warnings,
    )


def make_plan(payload: CampaignInput, context: PlanningContext) -> list[PlanItem]:
    requested_per_account = payload.posts_per_hour * payload.duration_hours
    if not payload.allow_media_reuse and payload.media_strategy != "same_media":
        requested_per_account = min(requested_per_account, len(context.media))

    items: list[PlanItem] = []
    random_decks: dict[uuid.UUID, list[Media]] = {}
    previous_random_media: dict[uuid.UUID, uuid.UUID] = {}
    for slot in range(requested_per_account):
        hour, position_in_hour = divmod(slot, payload.posts_per_hour)
        if payload.schedule_distribution == "even":
            offset_seconds = round((3600 / payload.posts_per_hour) * position_in_hour)
        elif payload.schedule_distribution == "burst":
            offset_seconds = position_in_hour * 30
        else:
            offset_seconds = position_in_hour * payload.post_cooldown_minutes * 60
        scheduled_at = context.starts_at + timedelta(hours=hour, seconds=offset_seconds)
        for account_position, account in enumerate(context.accounts):
            position = len(items)
            if payload.media_strategy == "same_media":
                medium = context.media[0]
            elif payload.media_strategy == "sequential":
                medium = context.media[(account_position + slot) % len(context.media)]
            else:
                cycle_number, cycle_position = divmod(slot, len(context.media))
                if cycle_position == 0:
                    deck = list(context.media)
                    random.Random(
                        f"{context.seed}:{account.id}:{cycle_number}"
                    ).shuffle(deck)
                    previous_media_id = previous_random_media.get(account.id)
                    if (
                        previous_media_id is not None
                        and len(deck) > 1
                        and deck[0].id == previous_media_id
                    ):
                        replacement_index = next(
                            index
                            for index, candidate in enumerate(deck[1:], start=1)
                            if candidate.id != previous_media_id
                        )
                        deck[0], deck[replacement_index] = (
                            deck[replacement_index],
                            deck[0],
                        )
                    random_decks[account.id] = deck
                    previous_random_media[account.id] = deck[-1].id
                medium = random_decks[account.id][cycle_position]
            items.append(
                PlanItem(
                    position=position,
                    account_id=account.id,
                    account_username=account.username,
                    media_id=medium.id,
                    media_name=medium.display_name,
                    scheduled_at=scheduled_at,
                )
            )
    return items


async def preview_campaign(
    payload: CampaignInput,
    owner_id: uuid.UUID,
    session: AsyncSession,
) -> tuple[CampaignPreview, PlanningContext | None]:
    context, errors, warnings = await load_context(payload, owner_id, session)
    items = make_plan(payload, context) if context else []
    return (
        CampaignPreview(
            valid=not errors,
            errors=errors,
            warnings=warnings,
            requested_jobs=payload.posts_per_hour
            * payload.duration_hours
            * len(set(payload.account_ids)),
            planned_jobs=len(items),
            planning_seed=context.seed if context else None,
            items=items[:500],
        ),
        context,
    )


async def apply_campaign_input(
    campaign: Campaign,
    payload: CampaignInput,
    session: AsyncSession,
) -> None:
    campaign.name = payload.name
    campaign.description = payload.description
    campaign.caption = payload.caption
    campaign.hashtags = [tag.lstrip("#").strip() for tag in payload.hashtags if tag.strip()]
    campaign.publication_type = payload.publication_type
    campaign.media_strategy = payload.media_strategy
    campaign.posts_per_hour = payload.posts_per_hour
    campaign.duration_hours = payload.duration_hours
    campaign.schedule_distribution = payload.schedule_distribution
    campaign.post_cooldown_minutes = payload.post_cooldown_minutes
    campaign.schedule_mode = payload.schedule_mode
    campaign.starts_at = payload.starts_at
    campaign.timezone = payload.timezone
    campaign.cover_mode = payload.cover_mode
    campaign.custom_cover_media_id = payload.custom_cover_media_id
    campaign.proxy_mode = payload.proxy_mode
    campaign.proxy_id = payload.proxy_id
    campaign.proxy_rotation_every = payload.proxy_rotation_every
    campaign.allow_media_reuse = payload.allow_media_reuse
    await session.execute(delete(CampaignAccount).where(CampaignAccount.campaign_id == campaign.id))
    await session.execute(delete(CampaignMedia).where(CampaignMedia.campaign_id == campaign.id))
    await session.execute(delete(CampaignProxy).where(CampaignProxy.campaign_id == campaign.id))
    for position, account_id in enumerate(dict.fromkeys(payload.account_ids)):
        session.add(
            CampaignAccount(campaign_id=campaign.id, account_id=account_id, position=position)
        )
    for position, media_id in enumerate(dict.fromkeys(payload.media_ids)):
        session.add(CampaignMedia(campaign_id=campaign.id, media_id=media_id, position=position))
    for priority, proxy_id in enumerate(dict.fromkeys(payload.proxy_ids), start=1):
        session.add(CampaignProxy(campaign_id=campaign.id, proxy_id=proxy_id, priority=priority))


async def activate_campaign(
    campaign: Campaign,
    payload: CampaignInput,
    owner_id: uuid.UUID,
    session: AsyncSession,
) -> CampaignPreview:
    if campaign.state not in {"draft", "paused"}:
        raise AppError(
            "campaign_state_conflict",
            "A campanha não pode ser ativada neste estado.",
            status_code=409,
        )
    preview, context = await preview_campaign(payload, owner_id, session)
    if not preview.valid or context is None:
        raise AppError(
            "campaign_not_ready",
            "A campanha possui bloqueios.",
            status_code=409,
            details=[{"message": item} for item in preview.errors],
        )
    await apply_campaign_input(campaign, payload, session)
    next_version = campaign.current_version + 1
    version = CampaignVersion(
        owner_id=owner_id,
        campaign_id=campaign.id,
        version=next_version,
        random_seed=context.seed,
        snapshot=payload.model_dump(mode="json"),
        created_at=utcnow(),
    )
    session.add(version)
    await session.flush()
    full_items = make_plan(payload, context)
    for item in full_items:
        raw_key = ":".join(
            (
                str(campaign.id),
                str(next_version),
                str(item.position),
                str(item.account_id),
                str(item.media_id),
                item.scheduled_at.isoformat(),
            )
        )
        session.add(
            Job(
                owner_id=owner_id,
                campaign_id=campaign.id,
                campaign_version_id=version.id,
                account_id=item.account_id,
                media_id=item.media_id,
                plan_position=item.position,
                rotation_slot=item.position // len(context.accounts),
                scheduled_at=item.scheduled_at,
                state="planned",
                idempotency_key=hashlib.sha256(raw_key.encode()).hexdigest(),
            )
        )
    campaign.current_version = next_version
    campaign.planned_count = len(full_items)
    campaign.succeeded_count = 0
    campaign.failed_count = 0
    campaign.state = "scheduled"
    campaign.starts_at = context.starts_at
    await session.commit()
    return preview
