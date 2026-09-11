"""Health and readiness endpoints."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request, Response, status

from specrag.api.schemas import HealthResponse, ReadyResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health():
    """Liveness probe — does not load models."""
    return HealthResponse(status="ok")


@router.get("/api/v1/ready", response_model=ReadyResponse)
async def ready(request: Request, response: Response):
    """Readiness probe — true after lifespan warmup."""
    from specrag.embedding import get_embedding_provider

    startup_ready = bool(getattr(request.app.state, "ready", False))
    embedding_ready = await asyncio.to_thread(get_embedding_provider().health) if startup_ready else False
    is_ready = startup_ready and embedding_ready
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyResponse(
        status="ok" if is_ready else "warming",
        ready=is_ready,
    )
