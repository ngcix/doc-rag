"""Document list, stats, upload, and delete routes."""

from __future__ import annotations

import asyncio
import os
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from specrag.api.schemas import (
    DocumentListItem,
    DocumentListResponse,
    JobResponse,
    NotImplementedResponse,
    StatsResponse,
)
from specrag.config import settings
from specrag.ingestion.loaders import SUPPORTED_EXTENSIONS
from specrag.ops import delete_document, get_stats, ingest_file, list_documents

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.get("", response_model=DocumentListResponse)
async def list_docs():
    docs = await asyncio.to_thread(list_documents)
    items = [DocumentListItem(**d) for d in docs]
    return DocumentListResponse(documents=items, total=len(items))


@router.get("/stats", response_model=StatsResponse)
async def documents_stats():
    stats = await asyncio.to_thread(get_stats)
    return StatsResponse(stats=stats)


@router.get("/download", response_class=FileResponse)
async def download_document(source: str):
    """Download a stored source document without exposing arbitrary host files."""
    documents_dir = settings.paths.documents_dir.resolve()
    path = Path(source).resolve()
    if not path.is_relative_to(documents_dir) or not path.is_file():
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(path, filename=path.name)


@router.post("/upload", response_model=JobResponse, status_code=202)
async def upload_document(request: Request, file: UploadFile):
    name = Path(file.filename or "").name
    if not name or name.startswith("."):
        raise HTTPException(status_code=400, detail="A file name is required")
    if Path(name).suffix.lower() not in SUPPORTED_EXTENSIONS:
        allowed = ", ".join(SUPPORTED_EXTENSIONS)
        raise HTTPException(status_code=400, detail=f"Unsupported file type; allowed: {allowed}")
    path = await asyncio.to_thread(_save_upload, file.file, name)
    job = request.app.state.jobs.submit("ingest", str(path), lambda: ingest_file(path))
    return JobResponse(**job.to_dict())


def _save_upload(source: BinaryIO, name: str) -> Path:
    """Write via a temp file so a running ingest never reads a partial file."""
    documents_dir = settings.paths.documents_dir
    documents_dir.mkdir(parents=True, exist_ok=True)
    target = (documents_dir / name).resolve()
    partial = documents_dir / f".{name}.{uuid.uuid4().hex}.part"
    try:
        with partial.open("wb") as out:
            shutil.copyfileobj(source, out)
        os.replace(partial, target)
    finally:
        partial.unlink(missing_ok=True)
    return target


@router.delete("", response_model=JobResponse, status_code=202)
async def delete_document_by_source(request: Request, source: str):
    job = request.app.state.jobs.submit("delete", source, lambda: delete_document(source))
    return JobResponse(**job.to_dict())


@router.get(
    "/{document_id}",
    response_model=NotImplementedResponse,
    status_code=501,
    summary="Get document by id (not implemented)",
)
async def get_document(document_id: str):
    raise HTTPException(
        status_code=501,
        detail=f"GET document '{document_id}' is not implemented in this phase",
    )
