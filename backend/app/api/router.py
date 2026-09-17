"""Application routes."""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health-check response."""

    status: Literal["healthy"]


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    """Report that the process is ready to serve requests."""
    return HealthResponse(status="healthy")
