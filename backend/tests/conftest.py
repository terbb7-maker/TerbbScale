import base64
import os

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_test")
os.environ.setdefault("SUPABASE_SECRET_KEY", "sb_secret_test")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/postgres",
)
os.environ.setdefault(
    "APP_ENCRYPTION_KEY",
    base64.urlsafe_b64encode(bytes(range(32))).decode(),
)
os.environ.setdefault("INTERNAL_API_KEY", "test-internal-key-at-least-32-characters")
