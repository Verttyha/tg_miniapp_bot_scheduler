from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Telegram Scheduler Mini App"
    app_env: str = Field(default="development", alias="APP_ENV")
    base_url: str = Field(default="http://localhost:8000", alias="BASE_URL")
    api_prefix: str = "/api"
    bot_token: str = Field(default="123456:CHANGE_ME", alias="BOT_TOKEN")
    bot_username: str = Field(default="telegram_scheduler_bot", alias="BOT_USERNAME")
    app_secret: str = Field(default="development-secret", alias="APP_SECRET")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    sqlite_path: str = Field(default="data/app.db", alias="SQLITE_PATH")
    allow_insecure_dev_auth: bool = Field(default=True, alias="ALLOW_INSECURE_DEV_AUTH")
    sync_telegram_webhook_on_startup: bool = Field(
        default=True,
        alias="SYNC_TELEGRAM_WEBHOOK_ON_STARTUP",
    )
    scheduler_interval_seconds: int = Field(default=300, alias="SCHEDULER_INTERVAL_SECONDS")
    reminder_minutes_before: int = 60
    telegram_init_data_ttl_seconds: int = 3600
    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    google_scopes: str = "https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/userinfo.email"
    yandex_client_id: str = Field(default="", alias="YANDEX_CLIENT_ID")
    yandex_client_secret: str = Field(default="", alias="YANDEX_CLIENT_SECRET")
    yandex_scopes: str = Field(default="", alias="YANDEX_SCOPES")

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    @property
    def resolved_sqlite_path(self) -> Path:
        return self.project_root / self.sqlite_path

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite+aiosqlite:///{self.resolved_sqlite_path.as_posix()}"

    @property
    def frontend_dist_dir(self) -> Path:
        return Path(__file__).resolve().parent / "static" / "app"

    @property
    def telegram_webhook_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/webhooks/telegram"

    @property
    def should_sync_telegram_webhook(self) -> bool:
        if not self.sync_telegram_webhook_on_startup:
            return False
        parsed = urlparse(self.base_url)
        hostname = (parsed.hostname or "").lower()
        return (
            parsed.scheme == "https"
            and hostname not in {"", "localhost", "127.0.0.1", "0.0.0.0"}
            and not hostname.endswith(".local")
        )

    @property
    def google_redirect_uri(self) -> str:
        return f"{self.base_url.rstrip('/')}/oauth/google/callback"

    @property
    def yandex_redirect_uri(self) -> str:
        return f"{self.base_url.rstrip('/')}/oauth/yandex/callback"


@lru_cache
def get_settings() -> Settings:
    return Settings()
