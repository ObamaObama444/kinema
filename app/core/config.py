from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/kinematics"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="Kinematics", alias="APP_NAME")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")

    database_url: str = Field(default=DEFAULT_DATABASE_URL, alias="DATABASE_URL")

    secret_key: str = Field(default="change-this-secret-key", alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=30,
        alias="ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    refresh_token_expire_minutes: int = Field(
        default=10080,
        alias="REFRESH_TOKEN_EXPIRE_MINUTES",
    )

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_bot_username: str = Field(default="", alias="TELEGRAM_BOT_USERNAME")
    miniapp_public_url: str = Field(
        default="",
        alias="MINIAPP_PUBLIC_URL",
    )
    mistral_api_key: str = Field(default="", alias="MISTRAL_API_KEY")
    mistral_api_base_url: str = Field(default="https://api.mistral.ai/v1", alias="MISTRAL_API_BASE_URL")
    mistral_plan_model: str = Field(default="mistral-small-2506", alias="MISTRAL_PLAN_MODEL")
    allow_insecure_telegram_dev_auth: bool = Field(
        default=True,
        alias="ALLOW_INSECURE_TELEGRAM_DEV_AUTH",
    )
    reminder_scheduler_enabled: bool = Field(default=True, alias="REMINDER_SCHEDULER_ENABLED")
    reminder_scheduler_interval_sec: int = Field(default=30, alias="REMINDER_SCHEDULER_INTERVAL_SEC")
    default_timezone: str = Field(default="UTC", alias="DEFAULT_TIMEZONE")

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug_flag(cls, value: bool | str | None) -> bool | str | None:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"debug", "dev", "development"}:
                return True
        return value

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str | None) -> str:
        url = str(value or "").strip()
        if not url:
            return DEFAULT_DATABASE_URL

        if url.startswith("postgres://"):
            return "postgresql+psycopg://" + url[len("postgres://") :]

        if url.startswith("postgresql://"):
            return "postgresql+psycopg://" + url[len("postgresql://") :]

        return url


settings = Settings()
