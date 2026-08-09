from types import SimpleNamespace

from app.workers.publisher import _finish_failed_campaign_if_complete


def test_campaign_is_closed_when_all_jobs_reach_a_terminal_state() -> None:
    campaign = SimpleNamespace(
        planned_count=2,
        succeeded_count=1,
        failed_count=1,
        state="running",
        completed_at=None,
    )

    _finish_failed_campaign_if_complete(campaign)  # type: ignore[arg-type]

    assert campaign.state == "completed_with_errors"
    assert campaign.completed_at is not None


def test_campaign_remains_running_while_jobs_are_pending() -> None:
    campaign = SimpleNamespace(
        planned_count=3,
        succeeded_count=1,
        failed_count=1,
        state="running",
        completed_at=None,
    )

    _finish_failed_campaign_if_complete(campaign)  # type: ignore[arg-type]

    assert campaign.state == "running"
    assert campaign.completed_at is None
