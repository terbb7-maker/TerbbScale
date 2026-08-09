from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql

from app.core.errors import AppError
from app.modules.dashboard.service import (
    EngagementPeriod,
    engagement_metrics_statement,
    engagement_window,
)

NOW = datetime(2026, 8, 1, 2, 30, tzinfo=UTC)


def test_today_uses_the_users_calendar_and_timezone() -> None:
    window = engagement_window(
        EngagementPeriod.TODAY,
        "America/Sao_Paulo",
        now=NOW,
    )

    assert window.date_from == date(2026, 7, 31)
    assert window.date_to == date(2026, 7, 31)
    assert window.starts_at == datetime(2026, 7, 31, 3, tzinfo=UTC)
    assert window.ends_at == datetime(2026, 8, 1, 3, tzinfo=UTC)


def test_yesterday_and_month_are_calendar_periods() -> None:
    yesterday = engagement_window(
        EngagementPeriod.YESTERDAY,
        "America/Sao_Paulo",
        now=NOW,
    )
    month = engagement_window(
        EngagementPeriod.MONTH,
        "America/Sao_Paulo",
        now=NOW,
    )

    assert yesterday.date_from == yesterday.date_to == date(2026, 7, 30)
    assert month.date_from == date(2026, 7, 1)
    assert month.date_to == date(2026, 7, 31)


def test_custom_period_is_inclusive() -> None:
    window = engagement_window(
        EngagementPeriod.CUSTOM,
        "UTC",
        date_from=date(2026, 7, 10),
        date_to=date(2026, 7, 12),
        now=NOW,
    )

    assert window.starts_at == datetime(2026, 7, 10, tzinfo=UTC)
    assert window.ends_at == datetime(2026, 7, 13, tzinfo=UTC)


@pytest.mark.parametrize(
    ("date_from", "date_to", "error_code"),
    [
        (None, None, "custom_period_dates_required"),
        (date(2026, 7, 20), date(2026, 7, 10), "invalid_custom_period"),
        (date(2026, 7, 1), date(2026, 8, 1), "future_custom_period"),
        (date(2025, 1, 1), date(2026, 7, 1), "custom_period_too_long"),
    ],
)
def test_custom_period_rejects_invalid_ranges(
    date_from: date | None,
    date_to: date | None,
    error_code: str,
) -> None:
    with pytest.raises(AppError) as error:
        engagement_window(
            EngagementPeriod.CUSTOM,
            "America/Sao_Paulo",
            date_from=date_from,
            date_to=date_to,
            now=NOW,
        )

    assert error.value.code == error_code


def test_metrics_query_uses_index_friendly_lateral_lookup() -> None:
    statement = engagement_metrics_statement(
        uuid4(),
        datetime(2026, 7, 1, tzinfo=UTC),
        datetime(2026, 8, 1, tzinfo=UTC),
    )
    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert "LATERAL" in sql
    assert "LIMIT" in sql
    assert "engagement_metrics" in sql
