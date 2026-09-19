"""Environment-backed DataCollector settings."""

from datetime import timedelta
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class DataCollectorSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://papertrading:papertrading@localhost:5432/papertrading"
    news_future_tolerance_minutes: int = 10
    news_query_limit: int = 200
    x_api_bearer_token: str | None = None
    market_poll_seconds: int = 60
    news_poll_seconds: int = 300
    social_poll_seconds: int = 900
    intelligence_poll_seconds: int = 120
    reaction_poll_seconds: int = 300
    health_poll_seconds: int = 60

    @property
    def future_tolerance(self) -> timedelta:
        return timedelta(minutes=self.news_future_tolerance_minutes)


@lru_cache
def get_data_collector_settings() -> DataCollectorSettings:
    return DataCollectorSettings()
