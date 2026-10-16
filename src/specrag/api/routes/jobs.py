"""Background job status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from specrag.api.schemas import JobListResponse, JobResponse

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.get("", response_model=JobListResponse)
async def list_jobs(request: Request):
    return JobListResponse(jobs=[JobResponse(**job.to_dict()) for job in request.app.state.jobs.list()])


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, request: Request):
    job = request.app.state.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return JobResponse(**job.to_dict())
