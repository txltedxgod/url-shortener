"""Application configuration loaded from environment variables.

Uses pydantic-settings so configuration is validated at startup and fails fast
if something is misconfigured in production.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    app_env: str = "production"
    app_name: str = "URL Shortener"
    app_debug: bool = False
    base_url: str = "http://localhost:8000"
    log_level: str = "INFO"

    # --- Postgres ---
    postgres_user: str = "shortener"
    postgres_password: str = "shortener"
    postgres_db: str = "shortener"
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    database_url: str | None = None

    # --- Redis ---
    redis_url: str = "redis://redis:6379/0"
    cache_ttl_seconds: int = 3600

    # --- Rate limiting ---
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60

    # --- Short codes ---
    shortcode_length: int = Field(default=7, ge=4, le=16)
    shortcode_max_retries: int = Field(default=6, ge=1, le=20)
    alias_min_length: int = Field(default=3, ge=1)
    alias_max_length: int = Field(default=32, le=64)

    # --- GeoIP ---
    geoip_db_path: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sqlalchemy_dsn(self) -> str:
        """Build the async SQLAlchemy DSN."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def alembic_dsn(self) -> str:
        """Synchronous DSN for Alembic migrations."""
        return self.sqlalchemy_dsn.replace("+asyncpg", "+psycopg").replace(
            "postgresql+psycopg", "postgresql"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()
