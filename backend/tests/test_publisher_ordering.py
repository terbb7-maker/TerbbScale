from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.workers import publisher


class AsyncSessionContext:
    def __init__(self, session: SimpleNamespace) -> None:
        self.session = session

    async def __aenter__(self) -> SimpleNamespace:
        return self.session

    async def __aexit__(self, *_args: object) -> None:
        return None


def session_factory(*sessions: SimpleNamespace):
    pending = iter(sessions)
    return lambda: AsyncSessionContext(next(pending))


@pytest.mark.asyncio
async def test_publication_waits_for_an_earlier_job_from_the_same_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = SimpleNamespace(
        state="queued",
        account_id=uuid4(),
        campaign_version_id=uuid4(),
        plan_position=4,
    )
    lookup_session = SimpleNamespace(get=AsyncMock(return_value=job))
    predecessor_session = SimpleNamespace(scalar=AsyncMock(return_value=uuid4()))
    redis = SimpleNamespace(
        set=AsyncMock(return_value=True),
        eval=AsyncMock(return_value=1),
    )
    unlocked = AsyncMock()
    monkeypatch.setattr(
        publisher,
        "SessionFactory",
        session_factory(lookup_session, predecessor_session),
    )
    monkeypatch.setattr(publisher, "get_redis", lambda: redis)
    monkeypatch.setattr(publisher, "_publish_job_unlocked", unlocked)

    assert await publisher.publish_job(uuid4()) is False
    unlocked.assert_not_awaited()
    redis.eval.assert_awaited_once()


@pytest.mark.asyncio
async def test_publication_runs_when_the_account_job_is_next_in_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = SimpleNamespace(
        state="queued",
        account_id=uuid4(),
        campaign_version_id=uuid4(),
        plan_position=4,
    )
    lookup_session = SimpleNamespace(get=AsyncMock(return_value=job))
    predecessor_session = SimpleNamespace(scalar=AsyncMock(return_value=None))
    redis = SimpleNamespace(
        set=AsyncMock(return_value=True),
        eval=AsyncMock(return_value=1),
    )
    unlocked = AsyncMock()
    monkeypatch.setattr(
        publisher,
        "SessionFactory",
        session_factory(lookup_session, predecessor_session),
    )
    monkeypatch.setattr(publisher, "get_redis", lambda: redis)
    monkeypatch.setattr(publisher, "_publish_job_unlocked", unlocked)

    job_id = uuid4()
    assert await publisher.publish_job(job_id) is True
    unlocked.assert_awaited_once_with(job_id)
    redis.eval.assert_awaited_once()


@pytest.mark.asyncio
async def test_publication_is_deferred_while_the_account_lock_is_busy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = SimpleNamespace(
        state="queued",
        account_id=uuid4(),
        campaign_version_id=uuid4(),
        plan_position=0,
    )
    lookup_session = SimpleNamespace(get=AsyncMock(return_value=job))
    redis = SimpleNamespace(set=AsyncMock(return_value=False))
    unlocked = AsyncMock()
    monkeypatch.setattr(publisher, "SessionFactory", session_factory(lookup_session))
    monkeypatch.setattr(publisher, "get_redis", lambda: redis)
    monkeypatch.setattr(publisher, "_publish_job_unlocked", unlocked)

    assert await publisher.publish_job(uuid4()) is False
    unlocked.assert_not_awaited()
