"""Callable operations shared by CLI and HTTP API."""

from specrag.ops.documents import (
    delete_document,
    get_chunk,
    get_stats,
    ingest_file,
    list_documents,
)
from specrag.ops.errors import (
    ChunkNotFoundError,
    DocumentNotFoundError,
    DuplicateTagError,
    OpsError,
    TagImmutableError,
    TagNotFoundError,
)
from specrag.ops.knowledge import add_knowledge, get_knowledge, update_knowledge
from specrag.ops.resolve import normalize_doc_id, resolve_chunk_id
from specrag.ops.search import multi_search, search_documents
from specrag.ops.tags import add_tag, list_tags, remove_tag, reset_tags

__all__ = [
    "ChunkNotFoundError",
    "DocumentNotFoundError",
    "DuplicateTagError",
    "OpsError",
    "TagImmutableError",
    "TagNotFoundError",
    "add_knowledge",
    "add_tag",
    "delete_document",
    "get_chunk",
    "get_knowledge",
    "get_stats",
    "ingest_file",
    "list_documents",
    "list_tags",
    "multi_search",
    "normalize_doc_id",
    "remove_tag",
    "reset_tags",
    "resolve_chunk_id",
    "search_documents",
    "update_knowledge",
]
