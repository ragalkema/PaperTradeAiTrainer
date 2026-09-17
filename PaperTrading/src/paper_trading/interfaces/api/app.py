"""Minimal PaperTrading status API."""

from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel

from paper_trading.infrastructure.configuration import get_settings
from paper_trading.infrastructure.logging import configure_logging


class HealthResponse(BaseModel):
    """Service health response."""

    status: Literal["healthy"]
    trading_mode: Literal["paper"]


def create_app() -> FastAPI:
    """Build the HTTP adapter without importing it into inner layers."""
    settings = get_settings()
    configure_logging(settings.log_level)
    application = FastAPI(title=settings.app_name, version="0.3.0")

    @application.get("/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        return HealthResponse(status="healthy", trading_mode="paper")

    return application


app = create_app()
