"""Search routes."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException

from specrag.api.schemas import SearchRequest, SearchResponse, SearchResultItem
from specrag.ops import multi_search, search_documents

router = APIRouter(prefix="/api/v1", tags=["search"])


def _images_only(body: SearchRequest) -> bool:
    if body.filters and body.filters.content_type:
        return body.filters.content_type.lower() == "image"
    return False


def _enrich_image_results(results, query: str):
    """Analyze image hits and attach descriptions to metadata."""
    from scripts.analyze_extracted_images import process_image

    for r in results:
        meta = getattr(r, "metadata", {}) or {}
        if meta.get("content_type") != "image":
            continue
        image_path = meta.get("image_path")
        if not image_path:
            continue
        success, analysis = process_image(Path(image_path), query=query)
        if success and analysis:
            meta["image_content"] = analysis
    return results


@router.post("/search", response_model=SearchResponse)
async def search(body: SearchRequest):
    use_hybrid = body.mode.value == "hybrid"
    images_only = _images_only(body)
    start = time.perf_counter()

    try:
        if body.queries and any(q.strip() for q in body.queries):
            queries = [q.strip() for q in body.queries if q.strip()]
            query_text = " | ".join(queries)
            results = await asyncio.to_thread(
                multi_search,
                queries=queries,
                top_k=body.top_k,
                images_only=images_only,
                use_hybrid=use_hybrid,
                save_results=False,
            )
        else:
            query_text = body.query.strip()
            results = await asyncio.to_thread(
                search_documents,
                query=query_text,
                top_k=body.top_k,
                images_only=images_only,
                use_hybrid=use_hybrid,
                save_results=False,
            )
        results = await asyncio.to_thread(_enrich_image_results, results, query_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    latency_ms = (time.perf_counter() - start) * 1000
    items = [
        SearchResultItem(**(r.to_dict() if hasattr(r, "to_dict") else {
            "rank": r.rank,
            "document": r.document,
            "similarity": round(r.similarity, 4),
            "metadata": r.metadata or {},
            "chunk_id": r.chunk_id,
        }))
        for r in results
    ]
    return SearchResponse(results=items, latency_ms=round(latency_ms, 2))
