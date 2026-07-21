"""Chunk id resolution helpers."""

from __future__ import annotations

from pathlib import Path

from specrag.ops._helpers import get_vector_store


def normalize_doc_id(doc_id: str) -> str:
    """Strip image extensions / path prefixes from a doc id."""
    image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".bmp"}
    path = Path(doc_id)
    if path.suffix.lower() in image_extensions:
        return str(path.with_suffix("")).replace("\\", "/").split("/")[-1]
    if "/" in doc_id or "\\" in doc_id:
        name = path.stem if path.suffix.lower() in image_extensions else path.name
        return name
    return doc_id


def resolve_chunk_id(identifier: str) -> str:
    """
    Resolve an identifier (chunk_id or image_path) to a store chunk_id.

    Returns the original identifier if no match is found.
    """
    from specrag.path_resolver import display_chunk_id, paths_refer_to_same_file

    vector_store = get_vector_store()

    metadata = vector_store.get_metadata(identifier)
    if metadata:
        return identifier

    all_docs = vector_store.list_documents()
    for doc_id in all_docs.keys():
        if display_chunk_id(doc_id) == identifier:
            return doc_id

    identifier_path = Path(identifier).name
    for doc_id in all_docs.keys():
        doc_metadata = vector_store.get_metadata(doc_id)
        if doc_metadata:
            img_path = doc_metadata.get("image_path", "")
            if img_path and (
                paths_refer_to_same_file(img_path, identifier, image=True)
                or Path(img_path).name == identifier_path
            ):
                return doc_id

    return identifier
