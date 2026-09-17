"""Environment-backed configuration at the framework edge."""

from decimal import Decimal
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings; exchange credentials are not exposed to bots or domain code."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "PaperTradeAiTrainer"
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://papertrading:papertrading@localhost:5432/papertrading"
    redis_url: str = "redis://localhost:6379/0"
    paper_starting_balance: Decimal = Decimal("10000")
    paper_fee_rate: Decimal = Decimal("0.0025")
    paper_slippage_rate: Decimal = Decimal("0.0005")
    market_symbols: str = "BTC-EUR,ETH-EUR,SOL-EUR"

    @property
    def configured_markets(self) -> tuple[str, ...]:
        return tuple(
            item.strip().upper() for item in self.market_symbols.split(",") if item.strip()
        )


@lru_cache
def get_settings() -> Settings:
    """Return process configuration."""
    return Settings()
