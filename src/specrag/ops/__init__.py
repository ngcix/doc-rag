"""Callable operations shared by CLI and HTTP API."""

from specrag.ops.errors import (
    ChunkNotFoundError,
    DuplicateTagError,
    OpsError,
    TagNotFoundError,
    TagImmutableError,
)
from specrag.ops.search import multi_search, search_documents
from specrag.ops.tags import add_tag, list_tags, remove_tag, reset_tags
from specrag.ops.knowledge import add_knowledge, get_knowledge, update_knowledge
from specrag.ops.documents import get_chunk, get_stats, list_documents
from specrag.ops.resolve import normalize_doc_id, resolve_chunk_id

__all__ = [
    "OpsError",
    "ChunkNotFoundError",
    "DuplicateTagError",
    "TagNotFoundError",
    "TagImmutableError",
    "search_documents",
    "multi_search",
    "add_tag",
    "remove_tag",
    "reset_tags",
    "list_tags",
    "add_knowledge",
    "update_knowledge",
    "get_knowledge",
    "list_documents",
    "get_stats",
    "get_chunk",
    "normalize_doc_id",
    "resolve_chunk_id",
]
