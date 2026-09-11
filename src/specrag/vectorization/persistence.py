"""Atomic persistence helpers for the local vector store."""

from __future__ import annotations

import json
import os
import pickle
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any


def _atomic_write(path: Path, writer: Callable[[Path], None]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        writer(temporary_path)
        with temporary_path.open("r+b") as temporary_file:
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, path)
        _fsync_parent_directory(path.parent)
    finally:
        temporary_path.unlink(missing_ok=True)


def _fsync_parent_directory(path: Path) -> None:
    if os.name == "nt":
        return
    directory_fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    def write(target: Path) -> None:
        with target.open("w", encoding="utf-8") as output:
            json.dump(payload, output, ensure_ascii=False, indent=2)

    _atomic_write(path, write)


def atomic_write_pickle(path: Path, payload: dict[str, Any]) -> None:
    def write(target: Path) -> None:
        with target.open("wb") as output:
            pickle.dump(payload, output, protocol=pickle.HIGHEST_PROTOCOL)

    _atomic_write(path, write)


def atomic_write_faiss(path: Path, index: Any) -> None:
    def write(target: Path) -> None:
        import faiss

        faiss.write_index(index, str(target))

    _atomic_write(path, write)
