"""Job endpoints — stubbed until ingest queue exists."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from specrag.api.schemas import NotImplementedResponse

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.get(
    "/{job_id}",
    response_model=NotImplementedResponse,
    status_code=501,
    summary="Get job status (not implemented)",
)
async def get_job(job_id: str):
    raise HTTPException(
        status_code=501,
        detail=f"Job status for '{job_id}' is not implemented in this phase",
    )
