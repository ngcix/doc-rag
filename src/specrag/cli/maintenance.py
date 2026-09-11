"""Local data maintenance commands."""

from __future__ import annotations

import shutil
from pathlib import Path

from specrag.config import (
    EXTRACTED_IMAGES_DIR,
    FAISS_INDEX_DIR,
    PROCESS_INPUT_DIR,
    PROCESS_OUTPUT_DIR,
    VECTORDB_DIR,
    ensure_directories,
)


def initialize() -> dict[str, str]:
    ensure_directories()
    return {
        "vector_db": str(VECTORDB_DIR),
        "faiss_index": str(FAISS_INDEX_DIR),
        "extracted_images": str(EXTRACTED_IMAGES_DIR),
    }


def clean_data(*, include_models: bool = False, confirmed: bool = False) -> None:
    from specrag.config import MODELS_DIR

    paths = [
        VECTORDB_DIR,
        FAISS_INDEX_DIR,
        EXTRACTED_IMAGES_DIR,
        PROCESS_INPUT_DIR,
        PROCESS_OUTPUT_DIR,
    ]
    if include_models:
        paths.append(MODELS_DIR)
    if not confirmed:
        answer = input("Delete generated SpecRAG data? [y/N]: ")
        if answer.lower() not in {"y", "yes"}:
            print("Cancelled.")
            return
    for path in paths:
        _clear_directory(path)
    ensure_directories()


def _clear_directory(path: Path) -> None:
    if not path.exists():
        return
    for item in path.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
