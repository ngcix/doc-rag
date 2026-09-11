"""Search routes."""

from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter, HTTPException

from specrag.api.schemas import SearchRequest, SearchResponse, SearchResultItem
from specrag.embedding import EmbeddingUnavailableError
from specrag.ops import multi_search, search_documents

router = APIRouter(prefix="/api/v1", tags=["search"])


def _images_only(body: SearchRequest) -> bool:
    if body.filters and body.filters.content_type:
        return body.filters.content_type.lower() == "image"
    return False


@router.post("/search", response_model=SearchResponse)
async def search(body: SearchRequest):
    use_hybrid = body.mode.value == "hybrid"
    images_only = _images_only(body)
    start = time.perf_counter()

    try:
        if body.queries and any(q.strip() for q in body.queries):
            queries = [q.strip() for q in body.queries if q.strip()]
            results = await asyncio.to_thread(
                multi_search,
                queries=queries,
                top_k=body.top_k,
                images_only=images_only,
                use_hybrid=use_hybrid,
                save_results=False,
            )
        else:
            results = await asyncio.to_thread(
                search_documents,
                query=body.query.strip(),
                top_k=body.top_k,
                images_only=images_only,
                use_hybrid=use_hybrid,
                save_results=False,
            )
    except EmbeddingUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    latency_ms = (time.perf_counter() - start) * 1000
    items = [
        SearchResultItem(
            **(
                r.to_dict()
                if hasattr(r, "to_dict")
                else {
                    "rank": r.rank,
                    "document": r.document,
                    "similarity": round(r.similarity, 4),
                    "metadata": r.metadata or {},
                    "chunk_id": r.chunk_id,
                }
            )
        )
        for r in results
    ]
    return SearchResponse(results=items, latency_ms=round(latency_ms, 2))
