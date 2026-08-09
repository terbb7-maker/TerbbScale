from fastapi import APIRouter
from sqlalchemy import select

from app.core.errors import AppError
from app.core.security import secret_box
from app.models.instagram import Setting
from app.modules.auth.dependencies import ActiveUserDep, SessionDep
from app.modules.settings.schemas import InstagramAppInput, PreferenceInput, SettingsOut

router = APIRouter(prefix="/settings", tags=["settings"])

REQUIRED_INSTAGRAM_SCOPES = {
    "instagram_business_basic",
    "instagram_business_content_publish",
    "instagram_business_manage_insights",
}


async def get_or_create(owner_id: object, session: SessionDep) -> Setting:
    setting = await session.scalar(select(Setting).where(Setting.owner_id == owner_id))
    if setting is None:
        setting = Setting(owner_id=owner_id)
        session.add(setting)
        await session.flush()
    return setting


def serialize(setting: Setting) -> SettingsOut:
    configured = bool(setting.instagram_app_secret_ciphertext)
    return SettingsOut(
        instagram_app_id=setting.instagram_app_id,
        app_secret_configured=configured,
        app_secret_masked="••••••••" if configured else None,
        redirect_uri=setting.redirect_uri,
        scopes=setting.scopes,
        timezone=setting.timezone,
        notifications_enabled=setting.notifications_enabled,
        app_verified=setting.app_verified_at is not None,
        app_last_error=setting.app_last_error,
    )


@router.get("", response_model=SettingsOut)
async def read_settings(user: ActiveUserDep, session: SessionDep) -> SettingsOut:
    setting = await get_or_create(user.id, session)
    await session.commit()
    return serialize(setting)


@router.put("/instagram-app", response_model=SettingsOut)
async def update_instagram_app(
    payload: InstagramAppInput,
    user: ActiveUserDep,
    session: SessionDep,
) -> SettingsOut:
    allowed = {
        *REQUIRED_INSTAGRAM_SCOPES,
        "instagram_business_manage_comments",
        "instagram_business_manage_messages",
    }
    if not set(payload.scopes).issubset(allowed):
        raise AppError("invalid_scopes", "Um ou mais scopes não são permitidos.")
    if not REQUIRED_INSTAGRAM_SCOPES.issubset(payload.scopes):
        raise AppError(
            "required_scopes_missing",
            "Os escopos de perfil, publicação e insights são obrigatórios.",
        )
    setting = await get_or_create(user.id, session)
    setting.instagram_app_id = payload.app_id
    setting.redirect_uri = str(payload.redirect_uri)
    setting.scopes = list(dict.fromkeys(payload.scopes))
    if payload.app_secret:
        setting.instagram_app_secret_ciphertext = secret_box.encrypt(
            payload.app_secret,
            context=f"instagram-app:{user.id}",
        )
    setting.app_verified_at = None
    setting.app_last_error = None
    await session.commit()
    return serialize(setting)


@router.put("/preferences", response_model=SettingsOut)
async def update_preferences(
    payload: PreferenceInput,
    user: ActiveUserDep,
    session: SessionDep,
) -> SettingsOut:
    setting = await get_or_create(user.id, session)
    setting.timezone = payload.timezone
    setting.notifications_enabled = payload.notifications_enabled
    user.timezone = payload.timezone
    await session.commit()
    return serialize(setting)
