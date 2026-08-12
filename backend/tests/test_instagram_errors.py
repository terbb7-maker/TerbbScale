from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.integrations.instagram import InstagramAPIError, InstagramClient


def test_authorization_url_reuses_existing_instagram_session() -> None:
    url = InstagramClient(app_id="instagram-app", app_secret="secret").authorization_url(
        redirect_uri="https://example.com/app/contas/callback",
        scopes=["instagram_business_basic", "instagram_business_content_publish"],
        state="oauth-state",
    )

    query = parse_qs(urlparse(url).query)
    assert "force_reauth" not in query
    assert query["client_id"] == ["instagram-app"]
    assert query["state"] == ["oauth-state"]


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
