from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.integrations.instagram import InstagramAPIError
from app.models.instagram import Account
from app.modules.accounts.health import (
    HealthAssessment,
    apply_health_assessment,
    apply_health_success,
    classify_instagram_error,
)


@pytest.mark.parametrize(
    ("code", "subcode", "error_class", "expected"),
    [
        (190, 463, "auth_expired", "reauth_required"),
        (190, 459, "auth_expired", "action_required"),
        (None, 459, "media_invalid", "action_required"),
        (368, None, "media_invalid", "temporarily_restricted"),
        (10, None, "permission_missing", "permission_required"),
        (4, None, "rate_limited", "provider_unavailable"),
        (2, None, "temporary_provider_error", "provider_unavailable"),
    ],
)
def test_official_provider_errors_map_to_account_health(
    code: int | None,
    subcode: int | None,
    error_class: str,
    expected: str,
) -> None:
    error = InstagramAPIError(
        error_class,
        "Meta response",
        retryable=error_class in {"rate_limited", "temporary_provider_error"},
        provider_code=code,
        provider_subcode=subcode,
    )
    result = classify_instagram_error(
        error,
        consecutive_failures=1,
        allow_inferred_suspension=True,
    )
    assert result is not None
    assert result.status == expected


def test_unknown_failure_only_becomes_possible_suspension_after_repetition() -> None:
    error = InstagramAPIError("unknown_provider_error", "Unavailable", retryable=False)
    first = classify_instagram_error(
        error,
        consecutive_failures=1,
        allow_inferred_suspension=True,
    )
    third = classify_instagram_error(
        error,
        consecutive_failures=3,
        allow_inferred_suspension=True,
    )
    assert first is not None and first.status == "unknown"
    assert third is not None and third.status == "possibly_suspended"


def test_media_error_does_not_mark_account_when_not_a_health_probe() -> None:
    error = InstagramAPIError("media_invalid", "Bad media", retryable=False)
    assert (
        classify_instagram_error(
            error,
            consecutive_failures=10,
            allow_inferred_suspension=False,
        )
        is None
    )


def account_with_health(status: str, *, connection_status: str) -> Account:
    now = datetime.now(UTC)
    return Account(
        id=uuid4(),
        owner_id=uuid4(),
        instagram_user_id="123",
        username="health_test",
        status=connection_status,
        health_status=status,
        health_confidence="confirmed",
        health_next_check_at=now,
        health_consecutive_failures=2,
        granted_scopes=[],
        connected_at=now,
    )


async def test_provider_outage_does_not_clear_existing_account_block() -> None:
    account = account_with_health("action_required", connection_status="error")
    session = MagicMock()
    assessment = HealthAssessment(
        "provider_unavailable",
        "confirmed",
        "Meta unavailable",
        "Wait",
        180,
    )

    await apply_health_assessment(session, account, assessment, source="scheduled")

    assert account.health_status == "action_required"
    assert account.status == "error"
    session.add.assert_not_called()


async def test_official_success_recovers_blocked_account() -> None:
    account = account_with_health("action_required", connection_status="error")
    session = MagicMock()

    await apply_health_success(session, account, source="scheduled")

    assert account.health_status == "operational"
    assert account.status == "connected"
    assert account.health_consecutive_failures == 0
    session.add.assert_called_once()
