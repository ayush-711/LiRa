"""Application configuration, loaded from environment variables.

All secrets and deployment-specific values come from the environment (or a local
`.env` during development). Nothing sensitive is hard-coded.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # Core
    app_name: str = "LiRa"
    environment: str = "development"
    app_base_url: str = "http://localhost"
    log_level: str = "INFO"

    # Security
    secret_key: str = "dev-insecure-secret-change-me"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14
    cookie_secure: bool = False
    cookie_domain: str = ""
    cors_origins: str = "http://localhost,http://localhost:3000"

    # Database
    postgres_user: str = "lira"
    postgres_password: str = "lira"
    postgres_db: str = "lira"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: str | None = None  # explicit override wins

    # File storage
    upload_root: str = "/data/uploads"
    max_upload_size_mb: int = 25

    # Email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    email_from: str = "LiRa <no-reply@lira.local>"

    # Activity feed retention: only the newest N events are kept (see
    # app/services/retention.py). The audit log is never pruned.
    activity_retention_limit: int = 100

    # Background jobs
    due_reminder_enabled: bool = True
    due_reminder_interval_hours: int = 24

    # Rate limiting (per client IP, applied to auth endpoints)
    auth_rate_limit_requests: int = 20
    auth_rate_limit_window_seconds: int = 300

    # Auth limits
    login_max_attempts: int = 5
    login_lockout_minutes: int = 15
    invitation_expire_hours: int = 72
    password_reset_expire_hours: int = 2

    # Optional integrations
    slack_webhook_url: str = ""

    # ── Derived ────────────────────────────────────────────────
    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def emails_enabled(self) -> bool:
        return bool(self.smtp_host)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
