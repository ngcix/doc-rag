"""Chunk metadata, tags, and knowledge routes."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request

from specrag.api.schemas import (
    ChunkResponse,
    KnowledgeBody,
    KnowledgeResponse,
    TagBody,
    TagMutationResponse,
    TagsResponse,
)
from specrag.embedding import EmbeddingUnavailableError
from specrag.ops import (
    add_knowledge,
    add_tag,
    get_chunk,
    get_knowledge,
    list_tags,
    remove_tag,
    reset_tags,
    update_knowledge,
)
from specrag.ops.errors import (
    ChunkNotFoundError,
    DuplicateTagError,
    OpsError,
    TagImmutableError,
    TagNotFoundError,
)

router = APIRouter(prefix="/api/v1/chunks", tags=["chunks"])


def _map_ops_error(exc: Exception) -> HTTPException:
    if isinstance(exc, EmbeddingUnavailableError):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, ChunkNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, DuplicateTagError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, TagNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, TagImmutableError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, OpsError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


@router.get("/{chunk_id}", response_model=ChunkResponse)
async def read_chunk(chunk_id: str):
    try:
        data = await asyncio.to_thread(get_chunk, chunk_id)
    except Exception as e:
        raise _map_ops_error(e) from e
    return ChunkResponse(**data)


@router.get("/{chunk_id}/tags", response_model=TagsResponse)
async def get_tags(chunk_id: str):
    try:
        data = await asyncio.to_thread(list_tags, chunk_id)
    except Exception as e:
        raise _map_ops_error(e) from e
    return TagsResponse(**data)


@router.post("/{chunk_id}/tags", response_model=TagMutationResponse)
async def post_tag(chunk_id: str, body: TagBody, request: Request):
    async with request.app.state.write_lock:
        try:
            result = await asyncio.to_thread(add_tag, chunk_id, body.tag)
        except Exception as e:
            raise _map_ops_error(e) from e
    return TagMutationResponse(
        chunk_id=result["chunk_id"],
        tag=body.tag,
        original_tags=result.get("original_tags", ""),
        user_tags=result.get("user_tags", ""),
        combined_tags=result.get("combined_tags", ""),
        message=f"Tag '{body.tag}' added",
    )


@router.delete("/{chunk_id}/tags", response_model=TagMutationResponse)
async def delete_tag(chunk_id: str, body: TagBody, request: Request):
    async with request.app.state.write_lock:
        try:
            result = await asyncio.to_thread(remove_tag, chunk_id, body.tag)
        except Exception as e:
            raise _map_ops_error(e) from e
    return TagMutationResponse(
        chunk_id=result["chunk_id"],
        tag=body.tag,
        original_tags=result.get("original_tags", ""),
        user_tags=result.get("user_tags", ""),
        combined_tags=result.get("combined_tags", ""),
        message=f"Tag '{body.tag}' removed",
    )


@router.post("/{chunk_id}/tags/reset", response_model=TagMutationResponse)
async def post_reset_tags(chunk_id: str, request: Request):
    async with request.app.state.write_lock:
        try:
            result = await asyncio.to_thread(reset_tags, chunk_id)
        except Exception as e:
            raise _map_ops_error(e) from e
    return TagMutationResponse(
        chunk_id=result["chunk_id"],
        original_tags=result.get("original_tags", ""),
        user_tags=result.get("user_tags", ""),
        combined_tags=result.get("combined_tags", ""),
        message=result.get("message") or "Tags reset to original",
    )


@router.get("/{chunk_id}/knowledge", response_model=KnowledgeResponse)
async def read_knowledge(chunk_id: str):
    try:
        data = await asyncio.to_thread(get_knowledge, chunk_id)
    except Exception as e:
        raise _map_ops_error(e) from e
    return KnowledgeResponse(**data)


@router.post("/{chunk_id}/knowledge", response_model=KnowledgeResponse)
async def post_knowledge(chunk_id: str, body: KnowledgeBody, request: Request):
    async with request.app.state.write_lock:
        try:
            result = await asyncio.to_thread(add_knowledge, chunk_id, body.knowledge)
        except Exception as e:
            raise _map_ops_error(e) from e
    return KnowledgeResponse(
        chunk_id=result["chunk_id"],
        knowledge=result["knowledge"],
        has_knowledge=True,
    )


@router.put("/{chunk_id}/knowledge", response_model=KnowledgeResponse)
async def put_knowledge(chunk_id: str, body: KnowledgeBody, request: Request):
    async with request.app.state.write_lock:
        try:
            result = await asyncio.to_thread(update_knowledge, chunk_id, body.knowledge)
        except Exception as e:
            raise _map_ops_error(e) from e
    return KnowledgeResponse(
        chunk_id=result["chunk_id"],
        knowledge=result["knowledge"],
        has_knowledge=True,
    )
