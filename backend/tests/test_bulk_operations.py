from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.accounts.schemas import AccountBulkRemoveInput
from app.modules.media.schemas import MediaBulkRemoveInput, MediaPreviewBatchInput
from app.modules.proxies.schemas import ProxyBulkRemoveInput


@pytest.mark.parametrize(
    "schema, field",
    [
        (AccountBulkRemoveInput, "account_ids"),
        (MediaBulkRemoveInput, "media_ids"),
        (MediaPreviewBatchInput, "media_ids"),
        (ProxyBulkRemoveInput, "proxy_ids"),
    ],
)
def test_bulk_payload_requires_at_least_one_id(schema: type, field: str) -> None:
    with pytest.raises(ValidationError):
        schema.model_validate({field: []})


def test_account_bulk_payload_rejects_duplicates() -> None:
    account_id = uuid4()
    with pytest.raises(ValidationError):
        AccountBulkRemoveInput(account_ids=[account_id, account_id])


@pytest.mark.parametrize(
    "schema, field",
    [
        (AccountBulkRemoveInput, "account_ids"),
        (MediaBulkRemoveInput, "media_ids"),
        (MediaPreviewBatchInput, "media_ids"),
        (ProxyBulkRemoveInput, "proxy_ids"),
    ],
)
def test_bulk_payload_accepts_up_to_200_ids(schema: type, field: str) -> None:
    payload = schema.model_validate({field: [uuid4() for _ in range(200)]})
    assert len(getattr(payload, field)) == 200
