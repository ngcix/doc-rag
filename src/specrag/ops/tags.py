"""Tag mutation and listing operations."""

from __future__ import annotations

import time
from typing import Any

from specrag.ops._helpers import (
    get_vector_store,
    rebuild_combined_tags,
    rebuild_content_with_tags,
    replace_chunk,
)
from specrag.ops.errors import (
    ChunkNotFoundError,
    DuplicateTagError,
    TagImmutableError,
    TagNotFoundError,
)
from specrag.ops.resolve import normalize_doc_id, resolve_chunk_id


def _load_chunk(doc_id: str):
    vector_store = get_vector_store()
    metadata = vector_store.get_metadata(doc_id)
    if not metadata:
        raise ChunkNotFoundError(f"Document {doc_id} not found.")
    content = vector_store.get_content(doc_id)
    if content is None:
        raise ChunkNotFoundError(f"Could not retrieve content for {doc_id}")
    return vector_store, metadata, content


def add_tag(doc_id: str, tag: str) -> dict[str, Any]:
    """Add a user tag and re-embed. Returns status dict."""
    doc_id = resolve_chunk_id(normalize_doc_id(doc_id))
    start_time = time.perf_counter()
    vector_store, current_metadata, current_content = _load_chunk(doc_id)

    original_tags = current_metadata.get("original_tags", current_metadata.get("tags", ""))
    user_tags = current_metadata.get("user_tags", "")

    existing_user_list = [t.strip() for t in user_tags.split(",") if t.strip()]
    if tag in existing_user_list:
        raise DuplicateTagError(f"Tag '{tag}' already exists in user tags.")

    new_user_tags = f"{user_tags},{tag}" if user_tags else tag
    new_combined_tags = rebuild_combined_tags(original_tags, new_user_tags)
    new_content = rebuild_content_with_tags(current_content, new_combined_tags)

    updated_metadata = current_metadata.copy()
    updated_metadata["tags"] = new_combined_tags
    updated_metadata["user_tags"] = new_user_tags
    if "original_tags" not in updated_metadata:
        updated_metadata["original_tags"] = original_tags

    embedding_time = replace_chunk(vector_store, doc_id, new_content, updated_metadata)
    total_time = time.perf_counter() - start_time

    return {
        "chunk_id": doc_id,
        "tag": tag,
        "original_tags": original_tags or "",
        "user_tags": new_user_tags,
        "combined_tags": new_combined_tags,
        "embedding_seconds": embedding_time,
        "total_seconds": total_time,
    }


def remove_tag(doc_id: str, tag: str) -> dict[str, Any]:
    """Remove a user tag and re-embed. Returns status dict."""
    doc_id = resolve_chunk_id(normalize_doc_id(doc_id))
    start_time = time.perf_counter()
    vector_store, current_metadata, current_content = _load_chunk(doc_id)

    original_tags = current_metadata.get("original_tags", "")
    user_tags = current_metadata.get("user_tags", "")

    original_list = [t.strip() for t in original_tags.split(",") if t.strip()]
    if tag in original_list:
        raise TagImmutableError(
            f"Cannot remove '{tag}' - it's an original (auto-extracted) tag."
        )

    user_list = [t.strip() for t in user_tags.split(",") if t.strip()]
    if tag not in user_list:
        raise TagNotFoundError(f"Tag '{tag}' not found in user tags.")

    user_list.remove(tag)
    new_user_tags = ",".join(user_list)
    new_combined_tags = rebuild_combined_tags(original_tags, new_user_tags)
    new_content = rebuild_content_with_tags(current_content, new_combined_tags)

    updated_metadata = current_metadata.copy()
    updated_metadata["tags"] = new_combined_tags
    updated_metadata["user_tags"] = new_user_tags

    embedding_time = replace_chunk(vector_store, doc_id, new_content, updated_metadata)
    total_time = time.perf_counter() - start_time

    return {
        "chunk_id": doc_id,
        "tag": tag,
        "original_tags": original_tags or "",
        "user_tags": new_user_tags,
        "combined_tags": new_combined_tags,
        "embedding_seconds": embedding_time,
        "total_seconds": total_time,
    }


def reset_tags(doc_id: str) -> dict[str, Any]:
    """Reset to original tags only. Returns status dict."""
    doc_id = resolve_chunk_id(normalize_doc_id(doc_id))
    start_time = time.perf_counter()
    vector_store, current_metadata, current_content = _load_chunk(doc_id)

    original_tags = current_metadata.get("original_tags", "")
    user_tags = current_metadata.get("user_tags", "")

    if not user_tags:
        return {
            "chunk_id": doc_id,
            "changed": False,
            "original_tags": original_tags or "",
            "user_tags": "",
            "combined_tags": original_tags or "",
            "message": f"No user tags to reset for document '{doc_id}'.",
        }

    new_content = rebuild_content_with_tags(current_content, original_tags)
    updated_metadata = current_metadata.copy()
    updated_metadata["tags"] = original_tags
    updated_metadata["user_tags"] = ""

    embedding_time = replace_chunk(vector_store, doc_id, new_content, updated_metadata)
    total_time = time.perf_counter() - start_time

    return {
        "chunk_id": doc_id,
        "changed": True,
        "removed_user_tags": user_tags,
        "original_tags": original_tags or "",
        "user_tags": "",
        "combined_tags": original_tags or "",
        "embedding_seconds": embedding_time,
        "total_seconds": total_time,
    }


def list_tags(doc_id: str) -> dict[str, Any]:
    """List original / user / combined tags for a chunk."""
    doc_id = resolve_chunk_id(normalize_doc_id(doc_id))
    vector_store = get_vector_store()
    metadata = vector_store.get_metadata(doc_id)
    if not metadata:
        raise ChunkNotFoundError(f"Document {doc_id} not found.")

    return {
        "chunk_id": doc_id,
        "original_tags": metadata.get("original_tags", "") or "",
        "user_tags": metadata.get("user_tags", "") or "",
        "combined_tags": metadata.get("tags", "") or "",
    }
