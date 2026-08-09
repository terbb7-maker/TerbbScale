from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.campaigns.schemas import CampaignInput
from app.modules.campaigns.service import PlanningContext, make_plan


def payload(strategy: str, *, posts: int = 4, reuse: bool = False) -> CampaignInput:
    return CampaignInput(
        name="Critical campaign",
        publication_type="reel",
        media_strategy=strategy,
        account_ids=[uuid4(), uuid4()],
        media_ids=[uuid4(), uuid4(), uuid4()],
        posts_per_hour=posts,
        duration_hours=1,
        schedule_mode="now",
        timezone="America/Sao_Paulo",
        allow_media_reuse=reuse,
    )


def context(input_data: CampaignInput) -> PlanningContext:
    accounts = [
        SimpleNamespace(id=item, username=f"account-{index}")
        for index, item in enumerate(input_data.account_ids)
    ]
    media = [
        SimpleNamespace(id=item, display_name=f"media-{index}")
        for index, item in enumerate(input_data.media_ids)
    ]
    return PlanningContext(
        accounts=accounts,  # type: ignore[arg-type]
        media=media,  # type: ignore[arg-type]
        starts_at=datetime(2026, 8, 1, tzinfo=UTC),
        seed="deterministic-seed",
    )


def test_same_media_distributes_accounts_and_reuses_first_media() -> None:
    input_data = payload("same_media")
    result = make_plan(input_data, context(input_data))
    assert len(result) == 8
    assert len({item.media_id for item in result}) == 1
    assert [item.account_id for item in result] == [
        input_data.account_ids[0],
        input_data.account_ids[1],
        input_data.account_ids[0],
        input_data.account_ids[1],
        input_data.account_ids[0],
        input_data.account_ids[1],
        input_data.account_ids[0],
        input_data.account_ids[1],
    ]


def test_posts_per_hour_are_applied_per_account() -> None:
    input_data = payload("same_media", posts=2).model_copy(update={"duration_hours": 2})
    result = make_plan(input_data, context(input_data))
    assert len(result) == 8
    assert sum(item.account_id == input_data.account_ids[0] for item in result) == 4
    assert sum(item.account_id == input_data.account_ids[1] for item in result) == 4
    assert result[0].scheduled_at == result[1].scheduled_at
    assert result[2].scheduled_at > result[0].scheduled_at


def test_sequential_without_reuse_limits_each_account_independently() -> None:
    input_data = payload("sequential", posts=9, reuse=False)
    result = make_plan(input_data, context(input_data))
    assert len(result) == 6
    for account_id in input_data.account_ids:
        account_media = [item.media_id for item in result if item.account_id == account_id]
        assert len(account_media) == 3
        assert set(account_media) == set(input_data.media_ids)


def test_sequential_advances_the_media_cycle_for_every_account() -> None:
    input_data = payload("sequential", posts=6, reuse=True)
    result = make_plan(input_data, context(input_data))
    first_account = [
        item.media_id for item in result if item.account_id == input_data.account_ids[0]
    ]
    second_account = [
        item.media_id for item in result if item.account_id == input_data.account_ids[1]
    ]
    assert first_account == input_data.media_ids * 2
    assert second_account == [
        input_data.media_ids[1],
        input_data.media_ids[2],
        input_data.media_ids[0],
        input_data.media_ids[1],
        input_data.media_ids[2],
        input_data.media_ids[0],
    ]


def test_random_plan_is_deterministic_and_unique_per_account_cycle() -> None:
    input_data = payload("random_without_replacement", posts=9, reuse=True)
    planning_context = context(input_data)
    first = make_plan(input_data, planning_context)
    second = make_plan(input_data, planning_context)
    assert [item.media_id for item in first] == [item.media_id for item in second]
    for account_id in input_data.account_ids:
        account_media = [item.media_id for item in first if item.account_id == account_id]
        for cycle_start in range(0, len(account_media), len(input_data.media_ids)):
            cycle = account_media[cycle_start : cycle_start + len(input_data.media_ids)]
            assert set(cycle) == set(input_data.media_ids)
        for boundary in range(
            len(input_data.media_ids),
            len(account_media),
            len(input_data.media_ids),
        ):
            assert account_media[boundary - 1] != account_media[boundary]


def test_custom_cover_is_accepted_for_reels() -> None:
    input_data = payload("same_media").model_dump()
    custom_cover_id = uuid4()
    input_data.update(
        cover_mode="custom",
        custom_cover_media_id=custom_cover_id,
    )
    validated = CampaignInput.model_validate(input_data)
    assert validated.cover_mode == "custom"
    assert validated.custom_cover_media_id == custom_cover_id


def test_custom_cover_is_rejected_for_non_reels() -> None:
    input_data = payload("same_media").model_dump()
    input_data.update(
        publication_type="feed",
        cover_mode="custom",
        custom_cover_media_id=uuid4(),
    )
    with pytest.raises(ValidationError, match="supported only for reels"):
        CampaignInput.model_validate(input_data)
