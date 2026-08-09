import httpx
import pytest

from app.integrations.instagram import InstagramAPIError, InstagramClient


@pytest.mark.parametrize(
    ("status", "error_class", "retryable"),
    [
        (429, "rate_limited", True),
        (503, "temporary_provider_error", True),
        (401, "auth_expired", False),
        (403, "permission_missing", False),
        (400, "media_invalid", False),
    ],
)
def test_provider_errors_are_classified(
    status: int,
    error_class: str,
    retryable: bool,
) -> None:
    response = httpx.Response(status, json={"error": {"message": "provider error"}})
    with pytest.raises(InstagramAPIError) as caught:
        InstagramClient._json_or_raise(response)
    assert caught.value.error_class == error_class
    assert caught.value.retryable is retryable
