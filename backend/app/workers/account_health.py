import uuid

import httpx
from sqlalchemy import select

from app.core.database import SessionFactory
from app.core.realtime import publish_user_event
from app.core.security import secret_box
from app.integrations.instagram import InstagramAPIError, InstagramClient
from app.models.instagram import Account, Setting, Token
from app.modules.accounts.health import (
    HealthAssessment,
    apply_health_assessment,
    apply_health_success,
    classify_instagram_error,
)
from app.modules.common import utcnow
from app.modules.proxies.service import ProxyManager


async def check_account_health(account_id: uuid.UUID, *, source: str = "scheduled") -> str:
    owner_id: uuid.UUID | None = None
    result_status = "unknown"
    async with SessionFactory() as session:
        account = await session.scalar(
            select(Account).where(Account.id == account_id, Account.removed_at.is_(None))
        )
        if account is None:
            return "not_found"
        owner_id = account.owner_id
        token = await session.scalar(
            select(Token)
            .where(Token.account_id == account.id, Token.revoked_at.is_(None))
            .order_by(Token.created_at.desc())
        )
        setting = await session.scalar(select(Setting).where(Setting.owner_id == account.owner_id))
        now = utcnow()
        if token is None or (token.expires_at is not None and token.expires_at <= now):
            assessment = HealthAssessment(
                "reauth_required",
                "confirmed",
                "O token da conta expirou ou não está mais disponível.",
                "Reconecte a conta pelo Instagram Login.",
                900,
            )
            await apply_health_assessment(session, account, assessment, source=source)
            result_status = assessment.status
        elif (
            setting is None
            or not setting.instagram_app_id
            or not setting.instagram_app_secret_ciphertext
        ):
            assessment = HealthAssessment(
                "unknown",
                "unknown",
                "Não foi possível verificar a conta porque o Instagram App não está configurado.",
                "Configure o Instagram App deste usuário.",
                900,
            )
            await apply_health_assessment(session, account, assessment, source=source)
            result_status = assessment.status
        else:
            try:
                app_secret = secret_box.decrypt(
                    setting.instagram_app_secret_ciphertext,
                    context=f"instagram-app:{account.owner_id}",
                )
                access_token = secret_box.decrypt(
                    token.token_ciphertext,
                    context=f"instagram-token:{account.owner_id}:{account.id}",
                )
                async with ProxyManager().create_client(None) as http_client:
                    profile = await InstagramClient(
                        app_id=setting.instagram_app_id,
                        app_secret=app_secret,
                        http_client=http_client,
                    ).profile(account.instagram_user_id, access_token)
                await apply_health_success(session, account, source=source, profile=profile)
                result_status = "operational"
            except InstagramAPIError as exc:
                assessment = classify_instagram_error(
                    exc,
                    consecutive_failures=account.health_consecutive_failures + 1,
                    allow_inferred_suspension=True,
                )
                if assessment is not None:
                    await apply_health_assessment(session, account, assessment, source=source)
                    result_status = assessment.status
            except httpx.HTTPError as exc:
                assessment = HealthAssessment(
                    "provider_unavailable",
                    "confirmed",
                    f"Falha temporária de conexão ({type(exc).__name__}).",
                    "Aguarde a próxima verificação automática.",
                    180,
                )
                await apply_health_assessment(session, account, assessment, source=source)
                result_status = assessment.status
            except Exception:
                assessment = HealthAssessment(
                    "unknown",
                    "unknown",
                    "O monitor encontrou uma falha interna ao verificar esta conta.",
                    "Tente novamente ou reconecte a conta se o problema persistir.",
                    300,
                )
                await apply_health_assessment(session, account, assessment, source=source)
                result_status = assessment.status
        await session.commit()
    if owner_id is not None:
        await publish_user_event(
            owner_id,
            "account.health_updated",
            {"account_id": str(account_id), "source": source},
        )
    return result_status


async def record_account_api_success(account_id: uuid.UUID, *, source: str) -> None:
    owner_id: uuid.UUID | None = None
    async with SessionFactory() as session:
        account = await session.get(Account, account_id)
        if account is None or account.removed_at is not None:
            return
        owner_id = account.owner_id
        await apply_health_success(session, account, source=source)
        await session.commit()
    if owner_id is not None:
        await publish_user_event(
            owner_id,
            "account.health_updated",
            {"account_id": str(account_id), "source": source},
        )


async def record_account_api_failure(
    account_id: uuid.UUID,
    error: InstagramAPIError,
    *,
    source: str,
) -> None:
    owner_id: uuid.UUID | None = None
    changed = False
    async with SessionFactory() as session:
        account = await session.get(Account, account_id)
        if account is None or account.removed_at is not None:
            return
        assessment = classify_instagram_error(
            error,
            consecutive_failures=account.health_consecutive_failures + 1,
            allow_inferred_suspension=False,
        )
        if assessment is None:
            return
        owner_id = account.owner_id
        await apply_health_assessment(session, account, assessment, source=source)
        await session.commit()
        changed = True
    if changed and owner_id is not None:
        await publish_user_event(
            owner_id,
            "account.health_updated",
            {"account_id": str(account_id), "source": source},
        )
