"""Document listing and chunk read operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specrag.config import settings
from specrag.graph import get_graph_store
from specrag.ops._helpers import get_vector_store
from specrag.ops.errors import ChunkNotFoundError, DocumentNotFoundError
from specrag.ops.resolve import normalize_doc_id, resolve_chunk_id
from specrag.tables import get_table_store


def list_documents() -> list[dict[str, Any]]:
    """Aggregate vectorized chunks by source_file."""
    vector_store = get_vector_store()
    documents = vector_store.list_documents()
    file_counts: dict[str, int] = {}
    for _, source in documents.items():
        source = source or "Unknown"
        file_counts[source] = file_counts.get(source, 0) + 1

    return [{"source": source, "chunk_count": count} for source, count in sorted(file_counts.items())]


def get_stats() -> dict[str, Any]:
    """Return vector DB statistics."""
    backend = settings.vectordb.backend.lower()
    if backend == "faiss":
        from specrag.vectorization.faiss_store import FaissVectorStore

        summary = FaissVectorStore.read_summary()
        if summary:
            return dict(summary)

    vector_store = get_vector_store()
    return dict(vector_store.get_stats())


def get_chunk(chunk_id: str, content_preview_chars: int = 500) -> dict[str, Any]:
    """Return metadata and a content preview for a chunk."""
    chunk_id = resolve_chunk_id(normalize_doc_id(chunk_id))
    vector_store = get_vector_store()
    metadata = vector_store.get_metadata(chunk_id)
    if not metadata:
        raise ChunkNotFoundError(f"Document {chunk_id} not found.")

    content = vector_store.get_content(chunk_id) or ""
    preview = content[:content_preview_chars]
    if len(content) > content_preview_chars:
        preview += "..."

    return {
        "chunk_id": chunk_id,
        "metadata": metadata,
        "content_preview": preview,
        "content_length": len(content),
    }


def _chunk_ids_for_source(vector_store, source: str) -> list[str]:
    return [chunk_id for chunk_id, chunk_source in vector_store.list_documents().items() if chunk_source == source]


def _stored_document(source: str) -> Path | None:
    """Return the file for ``source`` only if it lives inside documents_dir."""
    path = Path(source).resolve()
    if path.is_relative_to(settings.paths.documents_dir.resolve()) and path.is_file():
        return path
    return None


def delete_document(source: str) -> dict[str, Any]:
    """Remove a document's chunks from the index and its file from documents_dir."""
    vector_store = get_vector_store()
    chunk_ids = _chunk_ids_for_source(vector_store, source)
    path = _stored_document(source)
    if not chunk_ids and path is None:
        raise DocumentNotFoundError(f"Document {source} not found.")
    vector_store.delete(chunk_ids)
    get_graph_store().delete_document(source)
    get_table_store().delete_document(source)
    if path is not None:
        path.unlink()
    return {"source": source, "deleted_chunks": len(chunk_ids), "file_deleted": path is not None}


def ingest_file(path: Path) -> dict[str, Any]:
    """Index one file, replacing any chunks from a previous version of it."""
    from specrag.ingestion import ingest_documents

    path = path.resolve()
    source = str(path)
    vector_store = get_vector_store()
    replaced = _chunk_ids_for_source(vector_store, source)
    vector_store.delete(replaced)
    report = ingest_documents(files=[path], vector_store=vector_store)
    return {"source": source, **report.to_dict(), "replaced_chunks": len(replaced)}
