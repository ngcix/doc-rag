"""Shared helpers for ops modules."""

from __future__ import annotations

import re
from typing import Any


def get_vectorizer():
    from specrag.vectorization import get_vectorizer as _get

    return _get()


def get_vector_store():
    from specrag.vectorization import get_vector_store as _get

    return _get()


def get_search_engine():
    from specrag.search import get_search_engine as _get

    return _get()


def get_hybrid_search_engine_cls():
    from specrag.search import HybridSearchEngine

    return HybridSearchEngine


def rebuild_combined_tags(original_tags: str, user_tags: str) -> str:
    parts = []
    if original_tags:
        parts.append(original_tags)
    if user_tags:
        parts.append(user_tags)
    return ",".join(parts)


def rebuild_content_with_tags(base_content: str, all_tags: str) -> str:
    base_content = re.sub(r"\nTags:[^\n]*", "", base_content)
    base_content = re.sub(r"^Tags:[^\n]*\n?", "", base_content)
    base_content = re.sub(r"\n{3,}", "\n\n", base_content)
    base_content = base_content.strip()

    if all_tags:
        tag_boost_parts = ", ".join([all_tags] * 5)
        return base_content + f"\nTags: {tag_boost_parts}"
    return base_content


def filter_image_results(results: list[Any]) -> list[Any]:
    image_types = ["image", "extracted_image", "fullpage"]
    return [
        r
        for r in results
        if r.metadata.get("content_type") in image_types
        or r.metadata.get("type") in image_types
        or r.metadata.get("region_type") in ["fullpage", "figure", "table", "chart"]
    ]


def replace_chunk(
    vector_store,
    doc_id: str,
    content: str,
    metadata: dict,
) -> float:
    """Re-embed and atomically replace a chunk. Returns embedding seconds."""
    import time

    from specrag.vectorization.vectorizer import vectorize_text

    embedding_start = time.perf_counter()
    new_embedding = vectorize_text(content)[0].tolist()
    embedding_time = time.perf_counter() - embedding_start

    vector_store.delete([doc_id])
    vector_store.add(
        ids=[doc_id],
        embeddings=[new_embedding],
        documents=[content],
        metadatas=[metadata],
    )
    return embedding_time
