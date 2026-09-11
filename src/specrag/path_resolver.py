"""Resolve stored metadata paths against the current machine configuration."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import Optional

from specrag.config import BASE_DIR, DOCUMENTS_DIR, EXTRACTED_IMAGES_DIR

_TEXT_CHUNK_ID_RE = re.compile(r"^(?P<source>.+)_(?P<chunk_index>\d+)$")


def _to_portable_path(path_value: str | Path) -> Path:
    return Path(str(path_value).replace("\\", "/")).expanduser()


def _tail_after_marker(path: Path, marker: str) -> Path | None:
    parts = path.parts
    lowered = [part.lower() for part in parts]
    marker = marker.lower()
    if marker not in lowered:
        return None

    index = lowered.index(marker)
    tail = parts[index + 1 :]
    if not tail:
        return None
    return Path(*tail)


def _existing_or_first(candidates: Iterable[Path]) -> Path | None:
    first = None
    for candidate in candidates:
        if first is None:
            first = candidate
        if candidate.exists():
            return candidate.resolve()
    return first


def resolve_document_path(path_value: str | Path | None) -> Path | None:
    """Map a stored document path to the current configured documents_dir."""
    if not path_value:
        return None

    raw = _to_portable_path(path_value)
    candidates = []

    documents_tail = _tail_after_marker(raw, "documents")
    if documents_tail:
        candidates.append(Path(DOCUMENTS_DIR) / documents_tail)
    candidates.append(Path(DOCUMENTS_DIR) / raw.name)

    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.extend([BASE_DIR / raw, Path.cwd() / raw])

    return _existing_or_first(candidates)


def resolve_image_path(path_value: str | Path | None) -> Path | None:
    """Map a stored extracted image path to the current extracted_images dir."""
    if not path_value:
        return None

    raw = _to_portable_path(path_value)
    candidates = []

    images_tail = _tail_after_marker(raw, "extracted_images")
    if images_tail:
        candidates.append(Path(EXTRACTED_IMAGES_DIR) / images_tail)
    candidates.append(Path(EXTRACTED_IMAGES_DIR) / raw.name)

    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.extend([BASE_DIR / raw, Path.cwd() / raw])

    return _existing_or_first(candidates)


def normalize_metadata_paths(metadata: dict | None) -> dict:
    """Return metadata with source_file and image_path rebased for this machine."""
    normalized = dict(metadata or {})

    source_path = resolve_document_path(normalized.get("source_file"))
    if source_path is not None:
        normalized["source_file"] = str(source_path)

    image_path = resolve_image_path(normalized.get("image_path"))
    if image_path is not None:
        normalized["image_path"] = str(image_path)

    return normalized


def display_chunk_id(chunk_id: str | None) -> str:
    """Rebase path-like text chunk IDs for display while leaving image IDs intact."""
    if not chunk_id:
        return ""

    match = _TEXT_CHUNK_ID_RE.match(chunk_id)
    if not match:
        return chunk_id

    source = match.group("source")
    chunk_index = match.group("chunk_index")
    source_path = resolve_document_path(source)
    if source_path is None:
        return chunk_id

    return f"{source_path}_{chunk_index}"


def paths_refer_to_same_file(left: str | Path | None, right: str | Path | None, *, image: bool = False) -> bool:
    """Compare two stored/current paths after rebasing and by filename fallback."""
    resolver = resolve_image_path if image else resolve_document_path
    left_path = resolver(left)
    right_path = resolver(right)

    if left_path and right_path:
        if left_path == right_path:
            return True
        if left_path.name and left_path.name == right_path.name:
            return True

    return False
