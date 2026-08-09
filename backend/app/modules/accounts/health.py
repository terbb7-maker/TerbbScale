from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.instagram import InstagramAPIError, InstagramProfile
from app.models.instagram import Account, AccountHealthCheck
from app.models.operations import Notification
from app.modules.common import safe_external_payload, utcnow

BLOCKING_HEALTH_STATUSES = frozenset(
    {
        "reauth_required",
        "action_required",
        "permission_required",
        "temporarily_restricted",
        "possibly_suspended",
    }
)


@dataclass(frozen=True, slots=True)
class HealthAssessment:
    status: str
    confidence: str
    message: str
    action_required: str | None
    retry_after_seconds: int
    provider_code: int | None = None
    provider_subcode: int | None = None

    @property
    def blocks_publication(self) -> bool:
        return self.status in BLOCKING_HEALTH_STATUSES


def operational_assessment() -> HealthAssessment:
    return HealthAssessment(
        status="operational",
        confidence="confirmed",
        message="A conta respondeu normalmente à API oficial do Instagram.",
        action_required=None,
        retry_after_seconds=180,
    )


def classify_instagram_error(
    error: InstagramAPIError,
    *,
    consecutive_failures: int,
    allow_inferred_suspension: bool,
) -> HealthAssessment | None:
    code = error.provider_code
    subcode = error.provider_subcode
    message = str(error)[:1000]

    if subcode in {459, 464}:
        return HealthAssessment(
            "action_required",
            "confirmed",
            message,
            "Abra o Instagram e conclua a verificação solicitada pela Meta.",
            900,
            code,
            subcode,
        )
    if code == 190 or subcode in {458, 460, 463, 467} or error.error_class == "auth_expired":
        return HealthAssessment(
            "reauth_required",
            "confirmed",
            message,
            "Reconecte a conta pelo Instagram Login.",
            900,
            code,
            subcode,
        )
    if code == 368:
        return HealthAssessment(
            "temporarily_restricted",
            "confirmed",
            message,
            "Aguarde a liberação pela Meta e verifique a conta no Instagram.",
            900,
            code,
            subcode,
        )
    if (
        code == 10
        or (code is not None and 200 <= code <= 299)
        or error.error_class == "permission_missing"
    ):
        return HealthAssessment(
            "permission_required",
            "confirmed",
            message,
            "Reconecte a conta e conceda as permissões solicitadas.",
            900,
            code,
            subcode,
        )
    if code in {4, 17, 341} or error.status_code == 429 or error.error_class == "rate_limited":
        return HealthAssessment(
            "provider_unavailable",
            "confirmed",
            message,
            "Aguarde; o sistema verificará novamente sem bloquear a conta definitivamente.",
            180,
            code,
            subcode,
        )
    if code in {1, 2} or error.retryable or (error.status_code or 0) >= 500:
        return HealthAssessment(
            "provider_unavailable",
            "confirmed",
            message,
            "A Meta está temporariamente indisponível. Nenhuma reconexão é necessária agora.",
            180,
            code,
            subcode,
        )
    if allow_inferred_suspension and consecutive_failures >= 3:
        return HealthAssessment(
            "possibly_suspended",
            "inferred",
            message,
            "Abra o Instagram para confirmar se a conta foi suspensa ou exige uma ação.",
            900,
            code,
            subcode,
        )
    if allow_inferred_suspension:
        return HealthAssessment(
            "unknown",
            "unknown",
            message,
            "Aguarde novas verificações. Ainda não há evidência suficiente "
            "para classificar a conta.",
            180,
            code,
            subcode,
        )
    return None


async def apply_health_success(
    session: AsyncSession,
    account: Account,
    *,
    source: str,
    profile: InstagramProfile | None = None,
) -> None:
    assessment = operational_assessment()
    previous = account.health_status
    now = utcnow()
    account.health_status = assessment.status
    account.health_confidence = assessment.confidence
    account.health_source = source
    account.health_checked_at = now
    account.health_last_success_at = now
    account.health_next_check_at = now + timedelta(seconds=assessment.retry_after_seconds)
    account.health_consecutive_failures = 0
    account.health_error_code = None
    account.health_error_subcode = None
    account.health_message = assessment.message
    account.health_action_required = None
    if account.status != "removed":
        account.status = "connected"
    account.last_error_code = None
    if profile is not None:
        account.username = profile.username
        account.display_name = profile.name
        account.profile_picture_url = profile.profile_picture_url
        account.account_type = profile.account_type
    if previous != "operational" or source == "manual":
        add_health_history(session, account, assessment, source)


async def apply_health_assessment(
    session: AsyncSession,
    account: Account,
    assessment: HealthAssessment,
    *,
    source: str,
) -> None:
    previous = account.health_status
    now = utcnow()
    if previous in BLOCKING_HEALTH_STATUSES and not assessment.blocks_publication:
        # Uma falha inconclusiva ou indisponibilidade da Meta não comprova que a
        # conta bloqueada voltou a operar. Somente uma resposta oficial bem-sucedida
        # pode retirar esse bloqueio.
        account.health_source = source
        account.health_checked_at = now
        account.health_next_check_at = now + timedelta(seconds=assessment.retry_after_seconds)
        if source == "manual":
            add_health_history(session, account, assessment, source)
        return
    account.health_status = assessment.status
    account.health_confidence = assessment.confidence
    account.health_source = source
    account.health_checked_at = now
    account.health_next_check_at = now + timedelta(seconds=assessment.retry_after_seconds)
    if assessment.status != "provider_unavailable":
        account.health_consecutive_failures += 1
    account.health_error_code = (
        str(assessment.provider_code) if assessment.provider_code is not None else None
    )
    account.health_error_subcode = (
        str(assessment.provider_subcode) if assessment.provider_subcode is not None else None
    )
    account.health_message = assessment.message[:1000]
    account.health_action_required = assessment.action_required
    account.last_error_code = account.health_error_code or assessment.status
    if assessment.status == "reauth_required":
        account.status = "expired"
    elif assessment.blocks_publication:
        account.status = "error"
    if previous != assessment.status or source == "manual":
        add_health_history(session, account, assessment, source)
    if assessment.blocks_publication and previous not in BLOCKING_HEALTH_STATUSES:
        session.add(
            Notification(
                owner_id=account.owner_id,
                kind="account_action_required",
                title=f"Ação necessária em @{account.username}",
                message=assessment.action_required or assessment.message[:500],
                severity="error",
                data={
                    "account_id": str(account.id),
                    "health_status": assessment.status,
                },
            )
        )


def add_health_history(
    session: AsyncSession,
    account: Account,
    assessment: HealthAssessment,
    source: str,
) -> None:
    session.add(
        AccountHealthCheck(
            owner_id=account.owner_id,
            account_id=account.id,
            status=assessment.status,
            details=safe_external_payload(
                {
                    "confidence": assessment.confidence,
                    "source": source,
                    "provider_code": assessment.provider_code,
                    "provider_subcode": assessment.provider_subcode,
                    "message": assessment.message,
                    "action_required": assessment.action_required,
                }
            ),
            checked_at=utcnow(),
        )
    )
