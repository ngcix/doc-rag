"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from specrag.api.schemas import HealthResponse, ReadyResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health():
    """Liveness probe — does not load models."""
    return HealthResponse(status="ok")


@router.get("/api/v1/ready", response_model=ReadyResponse)
async def ready(request: Request):
    """Readiness probe — true after lifespan warmup."""
    is_ready = bool(getattr(request.app.state, "ready", False))
    return ReadyResponse(
        status="ok" if is_ready else "warming",
        ready=is_ready,
    )
