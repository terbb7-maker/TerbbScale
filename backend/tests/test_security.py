import pytest

from app.core.security import SecretBox, secret_box
from app.modules.common import safe_external_payload


def test_secret_box_round_trip_and_context_binding() -> None:
    encrypted = secret_box.encrypt("highly-sensitive", context="tenant:a")
    assert encrypted != "highly-sensitive"
    assert secret_box.decrypt(encrypted, context="tenant:a") == "highly-sensitive"
    with pytest.raises(Exception):
        secret_box.decrypt(encrypted, context="tenant:b")


def test_secret_box_rejects_short_keys() -> None:
    with pytest.raises(ValueError):
        SecretBox("dG9vLXNob3J0")


def test_external_payload_is_recursively_scrubbed() -> None:
    result = safe_external_payload(
        {
            "access_token": "secret",
            "nested": {"app_secret": "secret", "message": "safe"},
        }
    )
    assert result["access_token"] == "[REDACTED]"
    assert result["nested"] == {"app_secret": "[REDACTED]", "message": "safe"}
