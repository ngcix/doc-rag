"""Persistence mixin for the FAISS vector store."""

from __future__ import annotations

import json
import pickle
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

from specrag.config import VectorDBConfig, settings
from specrag.vectorization.persistence import (
    atomic_write_faiss,
    atomic_write_json,
    atomic_write_pickle,
)


def as_vectors(embeddings: dict) -> dict:
    """Store vectors as float32 arrays; Python float lists cost ~8x the memory."""
    import numpy as np

    return {doc_id: np.asarray(vector, dtype=np.float32) for doc_id, vector in embeddings.items()}


def read_store_summary(config: VectorDBConfig | None = None) -> dict | None:
    config = config or settings.vectordb
    path = config.faiss_index_dir / f"{config.collection_name}_summary.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Invalid FAISS summary: {path}") from exc


class FaissPersistenceMixin:
    config: VectorDBConfig
    _index: Any
    _metadata: dict
    _documents: dict
    _embeddings: dict
    _dimension: int | None
    _model_fingerprint: str | None
    _metadata_loaded: bool
    _embeddings_loaded: bool
    _index_needs_rebuild: bool

    def _rebuild_index(self) -> None:
        raise NotImplementedError

    def _snapshot_state(self) -> tuple:
        return (
            self._embeddings.copy(),
            self._documents.copy(),
            deepcopy(self._metadata),
            self._dimension,
            self._model_fingerprint,
        )

    def _restore_state(self, snapshot: tuple) -> None:
        (
            self._embeddings,
            self._documents,
            self._metadata,
            self._dimension,
            self._model_fingerprint,
        ) = snapshot
        self._rebuild_index()

    def _path(self, suffix: str) -> Path:
        return self.config.faiss_index_dir / f"{self.config.collection_name}{suffix}"

    @property
    def index_path(self) -> Path:
        return self._path(".index")

    @property
    def metadata_path(self) -> Path:
        return self._path("_metadata.pkl")

    @property
    def embeddings_path(self) -> Path:
        return self._path("_embeddings.pkl")

    @property
    def summary_path(self) -> Path:
        return self._path("_summary.json")

    def _ensure_metadata_loaded(self) -> None:
        if self._metadata_loaded:
            return
        self._metadata_loaded = True
        path = self._active_path("metadata")
        if not path.exists():
            if (read_store_summary(self.config) or {}).get("generation"):
                raise RuntimeError("Committed FAISS metadata generation is missing")
            return
        with path.open("rb") as source:
            data = pickle.load(source)
        self._metadata = data.get("metadata", {})
        self._documents = data.get("documents", {})
        self._dimension = data.get("dimension")
        self._model_fingerprint = data.get("model_fingerprint")
        legacy_embeddings = data.get("embeddings", {})
        if legacy_embeddings:
            self._embeddings = as_vectors(legacy_embeddings)
            self._embeddings_loaded = True
            self._index_needs_rebuild = True

    def _ensure_embeddings_loaded(self) -> None:
        if self._embeddings_loaded:
            return
        self._ensure_metadata_loaded()
        path = self._active_path("embeddings")
        if path.exists():
            with path.open("rb") as source:
                self._embeddings = as_vectors(pickle.load(source).get("embeddings", {}))
        elif (read_store_summary(self.config) or {}).get("generation"):
            raise RuntimeError("Committed FAISS embedding generation is missing")
        self._embeddings_loaded = True
        self._index_needs_rebuild = bool(self._embeddings)

    def _summary(self, generation: str | None = None) -> dict[str, Any]:
        summary = {
            "backend": "faiss",
            "collection_name": self.config.collection_name,
            "count": len(self._metadata),
            "index_type": self.config.faiss_index_type,
            "dimension": self._dimension,
            "distance_metric": self.config.distance_metric,
            "index_directory": str(self.config.faiss_index_dir),
            "model_fingerprint": self._model_fingerprint,
        }
        if generation:
            summary["generation"] = generation
        return summary

    def _active_path(self, kind: str) -> Path:
        summary = read_store_summary(self.config) or {}
        generation = summary.get("generation")
        if generation:
            return self._path(f"_{generation}_{kind}.pkl")
        return self.metadata_path if kind == "metadata" else self.embeddings_path

    def _save(self, include_embeddings: bool = True) -> None:
        del include_embeddings
        generation = uuid.uuid4().hex
        index_path = self._path(f"_{generation}.index")
        metadata_path = self._path(f"_{generation}_metadata.pkl")
        embeddings_path = self._path(f"_{generation}_embeddings.pkl")
        if self._index is not None:
            atomic_write_faiss(index_path, self._index)
        atomic_write_pickle(
            metadata_path,
            {
                "metadata": self._metadata,
                "documents": self._documents,
                "dimension": self._dimension,
                "model_fingerprint": self._model_fingerprint,
            },
        )
        atomic_write_pickle(embeddings_path, {"embeddings": self._embeddings})
        atomic_write_json(self.summary_path, self._summary(generation))
        self._cleanup_generations(generation)

    def _cleanup_generations(self, active_generation: str) -> None:
        prefix = f"{self.config.collection_name}_"
        for path in self.config.faiss_index_dir.glob(f"{prefix}*"):
            if path == self.summary_path or active_generation in path.name:
                continue
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        try:
            self.index_path.unlink(missing_ok=True)
        except OSError:
            pass

    def _delete_files(self) -> None:
        for path in self.config.faiss_index_dir.glob(f"{self.config.collection_name}*"):
            if path.name.endswith(".writer.lock"):
                continue
            path.unlink(missing_ok=True)
