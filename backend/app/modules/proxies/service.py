import asyncio
import ipaddress
import socket
import time
import uuid
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import quote

import httpx
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import secret_box
from app.models.campaigns import Campaign
from app.models.instagram import Account, AccountProxy, Proxy
from app.modules.common import utcnow
from app.modules.proxies.schemas import ProxyInput

PROXY_TEST_URL = "https://api.ipify.org?format=json"
PROXY_TEST_CONCURRENCY = 20
SCHEDULED_HEALTH_FAILURE_THRESHOLD = 3


def _is_dns_resolution_error(exc: BaseException) -> bool:
    """Inspect a wrapped httpx/httpcore exception without exposing its message."""
    current: BaseException | None = exc
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        if isinstance(current, socket.gaierror):
            return True
        visited.add(id(current))
        current = current.__cause__ or current.__context__
    return False


@dataclass(frozen=True, slots=True)
class ProxyCheckResult:
    status: str
    public_ip: str | None
    latency_ms: int | None
    checked_at: datetime
    error: str | None


@dataclass(frozen=True, slots=True)
class ParsedProxyEntry:
    host: str
    port: int
    username: str
    password: str


def parse_proxy_entry(value: str) -> ParsedProxyEntry:
    """Parse a conventional `host:port:username:password` proxy line safely."""
    parts = value.strip().split(":", 3)
    if len(parts) != 4 or not all(parts):
        raise ValueError("Use o formato host:porta:usuário:senha.")
    host, raw_port, username, password = parts
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ValueError("A porta deve ser um número entre 1 e 65535.") from exc
    # Reuse the same validation used by the individual form.
    validated = ProxyInput(
        name="proxy-import",
        protocol="http",
        host=host,
        port=port,
        username=username,
        password=password,
    )
    return ParsedProxyEntry(
        host=validated.host,
        port=validated.port,
        username=validated.username or "",
        password=validated.password or "",
    )


class ProxyManager:
    """Single boundary for proxy validation, testing and HTTP client construction."""

    def password_context(self, proxy: Proxy) -> str:
        return f"proxy-password:{proxy.owner_id}:{proxy.id}"

    def proxy_url(self, proxy: Proxy) -> str:
        auth = ""
        if proxy.username:
            username = quote(proxy.username, safe="")
            password = ""
            if proxy.password_ciphertext:
                password_value = secret_box.decrypt(
                    proxy.password_ciphertext, context=self.password_context(proxy)
                )
                password = ":" + quote(password_value, safe="")
            auth = f"{username}{password}@"
        return f"{proxy.protocol}://{auth}{proxy.host}:{proxy.port}"

    @asynccontextmanager
    async def create_client(self, proxy: Proxy | None) -> AsyncIterator[httpx.AsyncClient]:
        # A new client per execution prevents connection reuse across proxy identities.
        proxy_url = self.proxy_url(proxy) if proxy is not None else None
        async with httpx.AsyncClient(
            proxy=proxy_url,
            timeout=httpx.Timeout(30.0),
            follow_redirects=True,
        ) as client:
            yield client

    async def test(self, proxy: Proxy) -> ProxyCheckResult:
        checked_at = utcnow()
        started = time.perf_counter()
        try:
            async with self.create_client(proxy) as client:
                response = await client.get(PROXY_TEST_URL)
                response.raise_for_status()
            payload = response.json()
            public_ip = str(payload.get("ip", "")).strip() or None
            if public_ip:
                ipaddress.ip_address(public_ip)
            return ProxyCheckResult(
                status="online",
                public_ip=public_ip,
                latency_ms=round((time.perf_counter() - started) * 1000),
                checked_at=checked_at,
                error=None,
            )
        except (httpx.InvalidURL, ValueError):
            return ProxyCheckResult(
                status="offline",
                public_ip=None,
                latency_ms=None,
                checked_at=checked_at,
                error="Configuração inválida. Revise host, porta e credenciais.",
            )
        except httpx.TimeoutException:
            return ProxyCheckResult(
                status="offline",
                public_ip=None,
                latency_ms=None,
                checked_at=checked_at,
                error="Tempo limite ao conectar ao proxy.",
            )
        except httpx.ConnectError as exc:
            error = (
                "Não foi possível resolver o domínio do proxy (falha de DNS)."
                if _is_dns_resolution_error(exc)
                else "Não foi possível abrir conexão com o proxy."
            )
            return ProxyCheckResult(
                status="offline",
                public_ip=None,
                latency_ms=None,
                checked_at=checked_at,
                error=error,
            )
        except httpx.ProxyError:
            return ProxyCheckResult(
                status="offline",
                public_ip=None,
                latency_ms=None,
                checked_at=checked_at,
                error="O proxy recusou a conexão ou a autenticação.",
            )
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            error = (
                "O proxy recusou a autenticação (HTTP 407)."
                if status_code == 407
                else f"O teste recebeu uma resposta HTTP {status_code}."
            )
            return ProxyCheckResult(
                status="offline",
                public_ip=None,
                latency_ms=None,
                checked_at=checked_at,
                error=error,
            )
        except httpx.HTTPError as exc:
            return ProxyCheckResult(
                status="offline",
                public_ip=None,
                latency_ms=None,
                checked_at=checked_at,
                error=f"Não foi possível conectar ao proxy ({type(exc).__name__}).",
            )
        except Exception:
            # A failed health test must never make the proxy endpoints return 500.
            return ProxyCheckResult(
                status="offline",
                public_ip=None,
                latency_ms=None,
                checked_at=checked_at,
                error="Falha inesperada ao testar o proxy.",
            )

    async def test_many(
        self,
        proxies: Sequence[Proxy],
        *,
        concurrency: int = PROXY_TEST_CONCURRENCY,
    ) -> list[ProxyCheckResult]:
        """Test proxies concurrently while keeping outbound load bounded."""
        if concurrency < 1:
            raise ValueError("concurrency must be at least 1")
        semaphore = asyncio.Semaphore(concurrency)

        async def bounded_test(proxy: Proxy) -> ProxyCheckResult:
            async with semaphore:
                return await self.test(proxy)

        return list(await asyncio.gather(*(bounded_test(proxy) for proxy in proxies)))

    def apply_check(
        self,
        proxy: Proxy,
        result: ProxyCheckResult,
        *,
        failure_threshold: int = 1,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        proxy.last_check = result.checked_at
        proxy.last_error = result.error
        if result.status == "online":
            proxy.status = "online"
            proxy.public_ip = result.public_ip
            proxy.latency_ms = result.latency_ms
            proxy.cooldown_until = None
            proxy.consecutive_failures = 0
            return

        failures = proxy.consecutive_failures + 1
        proxy.consecutive_failures = failures
        if failures >= failure_threshold:
            proxy.status = "offline"
            proxy.public_ip = None
            proxy.latency_ms = None

    def apply_transport_failure(self, proxy: Proxy) -> None:
        """Temporarily remove an unstable proxy from account rotation."""
        failures = proxy.consecutive_failures + 1
        proxy.consecutive_failures = failures
        proxy.status = "offline"
        proxy.last_error = "Falha de conexão durante uma publicação."
        proxy.cooldown_until = utcnow() + timedelta(seconds=min(60 * (2 ** min(failures, 5)), 1800))


async def account_proxy(
    session: AsyncSession, *, account_id: uuid.UUID, owner_id: uuid.UUID
) -> Proxy | None:
    return await session.scalar(
        select(Proxy)
        .join(AccountProxy, AccountProxy.proxy_id == Proxy.id)
        .join(Account, Account.id == AccountProxy.account_id)
        .where(
            AccountProxy.account_id == account_id,
            Account.owner_id == owner_id,
            Proxy.owner_id == owner_id,
            Proxy.is_active.is_(True),
            AccountProxy.is_active.is_(True),
        )
        .order_by(AccountProxy.priority, AccountProxy.last_selected_at.asc().nullsfirst())
    )


async def select_account_publication_proxy(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    owner_id: uuid.UUID,
    exclude_proxy_id: uuid.UUID | None = None,
) -> tuple[Proxy | None, str]:
    """Atomically select a healthy proxy for a new publication of an account."""
    now = utcnow()
    account = await session.scalar(
        select(Account)
        .where(Account.id == account_id, Account.owner_id == owner_id)
        .with_for_update()
    )
    if account is None:
        return None, "account_not_found"
    rows = (
        await session.execute(
            select(AccountProxy, Proxy)
            .join(Proxy, Proxy.id == AccountProxy.proxy_id)
            .where(
                AccountProxy.account_id == account.id,
                AccountProxy.is_active.is_(True),
                Proxy.owner_id == owner_id,
                Proxy.is_active.is_(True),
                Proxy.status == "online",
                or_(Proxy.cooldown_until.is_(None), Proxy.cooldown_until <= now),
            )
            .order_by(AccountProxy.priority, AccountProxy.proxy_id)
        )
    ).all()
    if exclude_proxy_id is not None:
        rows = [row for row in rows if row[1].id != exclude_proxy_id]
    if not rows:
        return None, "no_healthy_proxy"

    current_index = next(
        (
            index
            for index, row in enumerate(rows)
            if row[1].id == account.proxy_rotation_current_proxy_id
        ),
        None,
    )
    selected_link: AccountProxy
    selected_proxy: Proxy
    if account.proxy_rotation_mode == "fixed":
        selected_link, selected_proxy = rows[0]
        reason = "fixed"
    elif (
        account.proxy_rotation_mode == "every_n_posts"
        and current_index is not None
        and account.proxy_rotation_counter < account.proxy_rotation_every
    ):
        selected_link, selected_proxy = rows[current_index]
        account.proxy_rotation_counter += 1
        reason = "rotation_interval"
    else:
        selected_link, selected_proxy = (
            rows[(current_index + 1) % len(rows)] if current_index is not None else rows[0]
        )
        account.proxy_rotation_current_proxy_id = selected_proxy.id
        account.proxy_rotation_counter = 1
        reason = (
            "rotation_per_post"
            if account.proxy_rotation_mode == "per_post"
            else "rotation_interval"
        )
    selected_link.last_selected_at = now
    return selected_proxy, reason


async def campaign_proxy(
    session: AsyncSession, *, campaign: Campaign, account: Account
) -> Proxy | None:
    if campaign.proxy_mode == "none":
        return None
    if campaign.proxy_mode == "account":
        return await account_proxy(session, account_id=account.id, owner_id=campaign.owner_id)
    if campaign.proxy_id is None:
        return None
    return await session.scalar(
        select(Proxy).where(
            Proxy.id == campaign.proxy_id,
            Proxy.owner_id == campaign.owner_id,
            Proxy.is_active.is_(True),
        )
    )
