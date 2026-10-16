"""Thread-safe, single-writer FAISS vector store."""

from __future__ import annotations

import threading

from specrag.config import VectorDBConfig, ensure_directories, settings
from specrag.embedding.base import ModelInfo
from specrag.path_resolver import normalize_metadata_paths
from specrag.vectorization.faiss_persistence import (
    FaissPersistenceMixin,
    as_vectors,
    read_store_summary,
)
from specrag.vectorization.writer_lease import WriterLease


class FaissVectorStore(FaissPersistenceMixin):
    """Local FAISS store. Run exactly one writer process per data volume."""

    def __init__(self, config: VectorDBConfig | None = None):
        self.config = config or settings.vectordb
        self._index = None
        self._metadata: dict[str, dict] = {}
        self._documents: dict[str, str] = {}
        self._embeddings: dict = {}  # doc_id -> float32 ndarray
        self._id_to_idx: dict[str, int] = {}
        self._idx_to_id: dict[int, str] = {}
        self._dimension: int | None = None
        self._model_fingerprint: str | None = None
        self._metadata_loaded = False
        self._embeddings_loaded = False
        self._index_needs_rebuild = False
        self._lock = threading.RLock()
        self._writer_lease = WriterLease(self._path(".writer.lock"))
        ensure_directories()

    @classmethod
    def read_summary(cls, config: VectorDBConfig | None = None) -> dict | None:
        return read_store_summary(config)

    def _ensure_index_ready(self) -> None:
        with self._lock:
            self._ensure_embeddings_loaded()
            if self._index_needs_rebuild:
                self._rebuild_index()
                self._index_needs_rebuild = False

    def _create_index(self, dimension: int):
        import faiss

        self._dimension = dimension
        index_type = self.config.faiss_index_type
        if index_type == "Flat":
            return faiss.IndexFlatIP(dimension) if self.config.distance_metric == "cosine" else faiss.IndexFlatL2(dimension)
        if index_type == "IVF":
            quantizer = faiss.IndexFlatL2(dimension)
            nlist = min(100, max(1, len(self._embeddings) // 10))
            return faiss.IndexIVFFlat(quantizer, dimension, nlist)
        if index_type == "HNSW":
            return faiss.IndexHNSWFlat(dimension, 32)
        raise ValueError(f"Unsupported FAISS index type: {index_type}")

    def _rebuild_index(self) -> None:
        if not self._embeddings:
            self._index = None
            self._id_to_idx = {}
            self._idx_to_id = {}
            self._index_needs_rebuild = False
            return
        import faiss
        import numpy as np

        ids = list(self._embeddings)
        matrix = np.asarray([self._embeddings[item] for item in ids], dtype=np.float32)
        if self.config.distance_metric == "cosine":
            faiss.normalize_L2(matrix)
        self._index = self._create_index(matrix.shape[1])
        if hasattr(self._index, "is_trained") and not self._index.is_trained:
            self._index.train(matrix)
        self._index.add(matrix)
        self._id_to_idx = {doc_id: index for index, doc_id in enumerate(ids)}
        self._idx_to_id = {index: doc_id for doc_id, index in self._id_to_idx.items()}
        self._index_needs_rebuild = False

    def validate_model(self, model_info: ModelInfo) -> None:
        with self._lock:
            self._ensure_metadata_loaded()
            if self._dimension and self._dimension != model_info.dimension:
                raise RuntimeError(f"Index dimension {self._dimension} does not match embedding dimension {model_info.dimension}")
            if self._metadata and not self._model_fingerprint:
                raise RuntimeError("Existing index has no model fingerprint; re-index required")
            if self._model_fingerprint and self._model_fingerprint != model_info.fingerprint:
                raise RuntimeError("Embedding model fingerprint does not match the index")
            if not self._metadata:
                self._model_fingerprint = model_info.fingerprint
                self._dimension = model_info.dimension

    def add(self, ids, embeddings, documents=None, metadatas=None) -> None:
        if not embeddings:
            return
        with self._lock:
            self._writer_lease.acquire()
            self._ensure_embeddings_loaded()
            self._validate_vectors(ids, embeddings)
            snapshot = self._snapshot_state()
            vectors = as_vectors(dict(zip(ids, embeddings)))
            try:
                for index, doc_id in enumerate(ids):
                    self._embeddings[doc_id] = vectors[doc_id]
                    if documents:
                        self._documents[doc_id] = documents[index]
                    if metadatas:
                        self._metadata[doc_id] = metadatas[index]
                self._model_fingerprint = self._model_fingerprint or settings.embedding.fingerprint
                self._rebuild_index()
                self._save()
            except Exception:
                self._restore_state(snapshot)
                raise

    def _validate_vectors(self, ids, embeddings) -> None:
        if len(ids) != len(embeddings):
            raise ValueError("ids and embeddings must have the same length")
        dimensions = {len(vector) for vector in embeddings}
        if len(dimensions) != 1:
            raise ValueError("All embeddings must have the same dimension")
        dimension = dimensions.pop()
        expected_dimension = self._dimension or settings.embedding.expected_dimension
        if dimension != expected_dimension:
            raise ValueError(f"Expected {expected_dimension} dimensions, got {dimension}")

    def replace(self, doc_id, embedding, document, metadata) -> None:
        self.add([doc_id], [embedding], [document], [metadata])

    def add_chunks(self, chunks: list[dict]) -> None:
        if not chunks:
            return
        metadatas = [
            {
                key: value if isinstance(value, (str, int, float, bool)) else str(value)
                for key, value in {
                    "source_file": chunk.get("source_file", ""),
                    **chunk.get("metadata", {}),
                }.items()
            }
            for chunk in chunks
        ]
        self.add(
            [chunk["chunk_id"] for chunk in chunks],
            [chunk["embedding"] for chunk in chunks],
            [chunk["content"] for chunk in chunks],
            metadatas,
        )

    def search_similar(self, query_embedding, top_k=5, threshold=None) -> list[dict]:
        with self._lock:
            self._ensure_index_ready()
            if self._index is None or self._index.ntotal == 0:
                return []
            import faiss
            import numpy as np

            query = np.asarray([query_embedding], dtype=np.float32)
            if query.shape[1] != self._dimension:
                raise ValueError("Query embedding dimension does not match index")
            if self.config.distance_metric == "cosine":
                faiss.normalize_L2(query)
            search_k = min(top_k * 4, self._index.ntotal)
            distances, indices = self._index.search(query, search_k)
            return self._format_results(distances[0], indices[0], top_k, threshold)

    def _format_results(self, distances, indices, top_k, threshold) -> list[dict]:
        results = []
        for distance, index in zip(distances, indices):
            doc_id = self._idx_to_id.get(int(index))
            if doc_id is None:
                continue
            similarity = float(distance) if self.config.distance_metric == "cosine" else 1 / (1 + float(distance))
            if threshold is not None and similarity < threshold:
                continue
            results.append(
                {
                    "id": doc_id,
                    "document": self._documents.get(doc_id),
                    "metadata": self._metadata.get(doc_id, {}),
                    "distance": float(distance),
                    "similarity": similarity,
                    "rank": len(results) + 1,
                }
            )
            if len(results) == top_k:
                break
        return results

    def delete(self, ids: list[str]) -> None:
        with self._lock:
            self._writer_lease.acquire()
            self._ensure_embeddings_loaded()
            snapshot = self._snapshot_state()
            changed = False
            for doc_id in ids:
                changed |= self._embeddings.pop(doc_id, None) is not None
                self._documents.pop(doc_id, None)
                self._metadata.pop(doc_id, None)
            if changed:
                try:
                    self._rebuild_index()
                    self._save()
                except Exception:
                    self._restore_state(snapshot)
                    raise

    def update_metadata(self, doc_id: str, metadata: dict) -> None:
        with self._lock:
            self._writer_lease.acquire()
            self._ensure_embeddings_loaded()
            if doc_id not in self._metadata:
                raise KeyError(doc_id)
            snapshot = self._snapshot_state()
            try:
                self._metadata[doc_id].update(metadata)
                self._save()
            except Exception:
                self._restore_state(snapshot)
                raise

    def get_metadata(self, doc_id: str) -> dict:
        with self._lock:
            self._ensure_metadata_loaded()
            return self._metadata.get(doc_id, {}).copy()

    def get_content(self, doc_id: str) -> str | None:
        with self._lock:
            self._ensure_metadata_loaded()
            return self._documents.get(doc_id)

    def get_indexed_documents(self) -> tuple[list[str], list[str]]:
        with self._lock:
            self._ensure_metadata_loaded()
            ids = list(self._documents)
            return ids, [self._documents[doc_id] for doc_id in ids]

    def clear(self) -> None:
        with self._lock:
            self._writer_lease.acquire()
            self._index = None
            self._metadata, self._documents, self._embeddings = {}, {}, {}
            self._id_to_idx, self._idx_to_id = {}, {}
            self._metadata_loaded = self._embeddings_loaded = True
            self._delete_files()

    def count(self) -> int:
        summary = read_store_summary(self.config)
        if summary and not self._metadata_loaded:
            return int(summary.get("count", 0))
        self._ensure_metadata_loaded()
        return len(self._metadata)

    def get_stats(self) -> dict:
        summary = read_store_summary(self.config)
        if summary and not self._metadata_loaded:
            return summary
        self._ensure_metadata_loaded()
        return self._summary()

    def list_documents(self) -> dict[str, str]:
        with self._lock:
            self._ensure_metadata_loaded()
            return {doc_id: normalize_metadata_paths(meta).get("source_file", "Unknown") for doc_id, meta in self._metadata.items()}

    def close(self) -> None:
        self._writer_lease.release()


_faiss_store: FaissVectorStore | None = None


def get_faiss_store() -> FaissVectorStore:
    global _faiss_store
    if _faiss_store is None:
        _faiss_store = FaissVectorStore()
    return _faiss_store


def close_faiss_store() -> None:
    global _faiss_store
    if _faiss_store is not None:
        _faiss_store.close()
        _faiss_store = None
