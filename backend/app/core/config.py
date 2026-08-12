from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    ENVIRONMENT: Literal["development", "test", "staging", "production"] = "development"
    APP_NAME: str = "PostX"
    APP_BASE_URL: str = "http://localhost"
    API_BASE_URL: str = "http://localhost/api/v1"
    CORS_ORIGINS: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    LOG_LEVEL: str = "INFO"
    BOOTSTRAP_ADMIN_EMAIL: str = ""

    SUPABASE_URL: AnyHttpUrl
    SUPABASE_PUBLISHABLE_KEY: str
    SUPABASE_SECRET_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "postx-media"
    COOKIE_STORY_ENABLED: bool = True

    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 8
    DATABASE_MAX_OVERFLOW: int = 4
    DATABASE_POOL_TIMEOUT: int = 10

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    APP_ENCRYPTION_KEY: str
    INTERNAL_API_KEY: str

    INSTAGRAM_API_VERSION: str = "v25.0"
    INSTAGRAM_GRAPH_BASE_URL: AnyHttpUrl = AnyHttpUrl("https://graph.instagram.com")
    INSTAGRAM_OAUTH_BASE_URL: AnyHttpUrl = AnyHttpUrl("https://www.instagram.com/oauth")
    TOKEN_RENEWAL_DAYS: int = 7

    SCHEDULER_INTERVAL_SECONDS: int = 60
    JOB_LEASE_SECONDS: int = 300
    MAX_PUBLICATION_ATTEMPTS: int = 6
    MEDIA_RETENTION_DAYS: int = 7
    LOG_RETENTION_DAYS: int = 90
    AUDIT_RETENTION_DAYS: int = 365

    @field_validator("DATABASE_URL")
    @classmethod
    def require_asyncpg(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use postgresql+asyncpg")
        return value

    @field_validator("SUPABASE_SECRET_KEY")
    @classmethod
    def require_secret_in_production(cls, value: str, info: object) -> str:
        return value

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
