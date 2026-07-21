"""Document list / stats and greenfield stubs."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from specrag.api.schemas import (
    DocumentListItem,
    DocumentListResponse,
    NotImplementedResponse,
    StatsResponse,
)
from specrag.ops import get_stats, list_documents

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


@router.post(
    "/upload",
    response_model=NotImplementedResponse,
    status_code=501,
    summary="Upload document (not implemented)",
)
async def upload_document():
    raise HTTPException(
        status_code=501,
        detail="Document upload / ingest jobs are not implemented in this phase",
    )


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


@router.delete(
    "/{document_id}",
    response_model=NotImplementedResponse,
    status_code=501,
    summary="Delete document (not implemented)",
)
async def delete_document(document_id: str):
    raise HTTPException(
        status_code=501,
        detail=f"DELETE document '{document_id}' is not implemented in this phase",
    )
