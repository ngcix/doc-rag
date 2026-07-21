"""Knowledge enrichment operations."""

from __future__ import annotations

import time
from typing import Any

from specrag.ops._helpers import get_vector_store, replace_chunk
from specrag.ops.errors import ChunkNotFoundError
from specrag.ops.resolve import resolve_chunk_id


def _load_chunk(doc_id: str):
    vector_store = get_vector_store()
    metadata = vector_store.get_metadata(doc_id)
    if not metadata:
        raise ChunkNotFoundError(f"Document {doc_id} not found.")
    content = vector_store.get_content(doc_id)
    if content is None:
        raise ChunkNotFoundError(f"Could not retrieve content for {doc_id}")
    return vector_store, metadata, content


def add_knowledge(identifier: str, knowledge_text: str) -> dict[str, Any]:
    """Append knowledge and re-embed."""
    doc_id = resolve_chunk_id(identifier)
    start_time = time.perf_counter()
    vector_store, current_metadata, current_content = _load_chunk(doc_id)

    current_knowledge = current_metadata.get("knowledge", "")
    if current_knowledge:
        new_knowledge = f"{current_knowledge}\n\n{knowledge_text}"
    else:
        new_knowledge = knowledge_text

    knowledge_boost = f"\n\n---\nKnowledge:\n{knowledge_text}"
    new_content = current_content + knowledge_boost

    updated_metadata = current_metadata.copy()
    updated_metadata["knowledge"] = new_knowledge

    embedding_time = replace_chunk(vector_store, doc_id, new_content, updated_metadata)
    total_time = time.perf_counter() - start_time

    return {
        "chunk_id": doc_id,
        "knowledge": new_knowledge,
        "embedding_seconds": embedding_time,
        "total_seconds": total_time,
    }


def update_knowledge(identifier: str, knowledge_text: str) -> dict[str, Any]:
    """Replace knowledge entirely and re-embed."""
    doc_id = resolve_chunk_id(identifier)
    start_time = time.perf_counter()
    vector_store, current_metadata, current_content = _load_chunk(doc_id)

    if "\n\n---\nKnowledge:" in current_content:
        base_content = current_content.split("\n\n---\nKnowledge:")[0]
    else:
        base_content = current_content

    knowledge_boost = f"\n\n---\nKnowledge:\n{knowledge_text}"
    new_content = base_content + knowledge_boost

    updated_metadata = current_metadata.copy()
    updated_metadata["knowledge"] = knowledge_text

    embedding_time = replace_chunk(vector_store, doc_id, new_content, updated_metadata)
    total_time = time.perf_counter() - start_time

    return {
        "chunk_id": doc_id,
        "knowledge": knowledge_text,
        "embedding_seconds": embedding_time,
        "total_seconds": total_time,
    }


def get_knowledge(identifier: str) -> dict[str, Any]:
    """Return knowledge text for a chunk."""
    doc_id = resolve_chunk_id(identifier)
    vector_store = get_vector_store()
    metadata = vector_store.get_metadata(doc_id)
    if not metadata:
        raise ChunkNotFoundError(f"Document {doc_id} not found.")

    knowledge = metadata.get("knowledge", "") or ""
    return {
        "chunk_id": doc_id,
        "knowledge": knowledge,
        "has_knowledge": bool(knowledge),
    }
