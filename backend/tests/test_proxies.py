import asyncio
import socket
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from app.core.security import secret_box
from app.models.instagram import Proxy
from app.modules.accounts.schemas import AccountProxyPoolInput
from app.modules.campaigns.schemas import CampaignInput
from app.modules.proxies.schemas import ProxyImportInput, ProxyInput
from app.modules.proxies.service import (
    ProxyCheckResult,
    ProxyManager,
    _is_dns_resolution_error,
    parse_proxy_entry,
)


def test_proxy_input_rejects_url_in_host() -> None:
    with pytest.raises(ValidationError, match="Host inválido"):
        ProxyInput(name="Proxy", protocol="http", host="https://proxy.example", port=8080)


def test_proxy_url_escapes_credentials_without_exposing_ciphertext() -> None:
    proxy = Proxy(
        id=uuid4(),
        owner_id=uuid4(),
        name="tenant proxy",
        protocol="socks5",
        host="127.0.0.1",
        port=1080,
        username="name@example",
    )
    manager = ProxyManager()
    proxy.password_ciphertext = secret_box.encrypt(
        "pa:ss@word", context=manager.password_context(proxy)
    )
    url = manager.proxy_url(proxy)
    assert url == "socks5://name%40example:pa%3Ass%40word@127.0.0.1:1080"
    assert proxy.password_ciphertext not in url


def test_dns_resolution_error_is_found_inside_httpx_chain() -> None:
    try:
        try:
            raise socket.gaierror(-2, "name not known")
        except socket.gaierror as exc:
            raise httpx.ConnectError("connection failed") from exc
    except httpx.ConnectError as exc:
        assert _is_dns_resolution_error(exc)


def test_scheduled_health_check_requires_three_failures_before_offline() -> None:
    proxy = Proxy(
        id=uuid4(),
        owner_id=uuid4(),
        name="tenant proxy",
        protocol="http",
        host="proxy.example.test",
        port=8080,
        status="online",
        consecutive_failures=0,
        public_ip="203.0.113.10",
        latency_ms=250,
    )
    result = ProxyCheckResult(
        status="offline",
        public_ip=None,
        latency_ms=None,
        checked_at=datetime.now(UTC),
        error="Falha de DNS.",
    )
    manager = ProxyManager()

    manager.apply_check(proxy, result, failure_threshold=3)
    manager.apply_check(proxy, result, failure_threshold=3)
    assert proxy.status == "online"
    assert proxy.public_ip == "203.0.113.10"
    assert proxy.consecutive_failures == 2

    manager.apply_check(proxy, result, failure_threshold=3)
    assert proxy.status == "offline"
    assert proxy.public_ip is None
    assert proxy.consecutive_failures == 3


@pytest.mark.asyncio
async def test_bulk_proxy_checks_keep_concurrency_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = ProxyManager()
    active = 0
    maximum = 0

    async def fake_test(proxy: Proxy) -> ProxyCheckResult:
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        try:
            await asyncio.sleep(0)
            return ProxyCheckResult(
                status="online",
                public_ip="203.0.113.10",
                latency_ms=1,
                checked_at=datetime.now(UTC),
                error=None,
            )
        finally:
            active -= 1

    monkeypatch.setattr(manager, "test", fake_test)
    proxies = [
        Proxy(
            id=uuid4(),
            owner_id=uuid4(),
            name=f"Proxy {index}",
            protocol="http",
            host="proxy.example.test",
            port=8080,
        )
        for index in range(8)
    ]

    results = await manager.test_many(proxies, concurrency=3)

    assert len(results) == 8
    assert maximum == 3


def test_fixed_campaign_proxy_requires_an_id() -> None:
    values = {
        "name": "Campaign",
        "publication_type": "reel",
        "media_strategy": "same_media",
        "account_ids": [uuid4()],
        "media_ids": [uuid4()],
        "posts_per_hour": 1,
        "duration_hours": 1,
        "schedule_mode": "now",
        "timezone": "UTC",
        "proxy_mode": "fixed",
    }
    with pytest.raises(ValidationError, match="proxy_id is required"):
        CampaignInput.model_validate(values)


def test_parse_conventional_proxy_entry() -> None:
    entry = parse_proxy_entry("proxy.example.test:10000:sample-user:sample-password")
    assert entry.host == "proxy.example.test"
    assert entry.port == 10000
    assert entry.username == "sample-user"
    assert entry.password == "sample-password"


def test_import_limits_batch_size() -> None:
    entries = "\n".join("proxy.example:1000:user:password" for _ in range(501))
    with pytest.raises(ValidationError, match="no máximo 500"):
        ProxyImportInput(entries=entries)


def test_rotation_pool_rejects_duplicate_proxy_and_invalid_interval() -> None:
    proxy_id = uuid4()
    with pytest.raises(ValidationError, match="não pode ser repetida"):
        AccountProxyPoolInput(proxy_ids=[proxy_id, proxy_id], rotation_mode="per_post")
    with pytest.raises(ValidationError, match="só pode ser configurado"):
        AccountProxyPoolInput(proxy_ids=[proxy_id], rotation_mode="fixed", rotate_every=2)
