from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_base_url: str = "http://localhost:8000"

    database_url: str

    telegram_bot_token: str
    telegram_webhook_secret: str
    telegram_allowed_user_ids: str = Field(default="")

    openai_api_key: str
    openai_transcription_model: str = "whisper-1"
    openai_text_model: str = "gpt-5.5"

    weekly_report_cron_token: str
    report_timezone: str = "America/Bogota"
    report_day: int = 0
    report_lookback_days: int = 7

    @property
    def allowed_user_ids(self) -> set[int]:
        ids = set()
        for raw_id in self.telegram_allowed_user_ids.split(","):
            raw_id = raw_id.strip()
            if raw_id:
                ids.add(int(raw_id))
        return ids

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
