from pydantic import BaseModel, Field, HttpUrl


class SettingsOut(BaseModel):
    instagram_app_id: str | None
    app_secret_configured: bool
    app_secret_masked: str | None
    redirect_uri: str | None
    scopes: list[str]
    timezone: str
    notifications_enabled: bool
    app_verified: bool
    app_last_error: str | None


class InstagramAppInput(BaseModel):
    app_id: str = Field(min_length=3, max_length=128)
    app_secret: str | None = Field(default=None, min_length=8, max_length=512)
    redirect_uri: HttpUrl
    scopes: list[str] = Field(
        default_factory=lambda: [
            "instagram_business_basic",
            "instagram_business_content_publish",
            "instagram_business_manage_insights",
        ]
    )


class PreferenceInput(BaseModel):
    timezone: str = Field(min_length=1, max_length=64)
    notifications_enabled: bool = True
