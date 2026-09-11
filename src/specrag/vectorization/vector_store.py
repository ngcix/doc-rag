"""Optional ChromaDB vector store backend."""

from __future__ import annotations

from typing import Optional

from specrag.config import VectorDBConfig, ensure_directories, settings
from specrag.embedding.base import ModelInfo
from specrag.path_resolver import normalize_metadata_paths


class VectorStore:
    def __init__(self, config: VectorDBConfig | None = None):
        self.config = config or settings.vectordb
        self._client = None
        self._collection = None
        ensure_directories()

    @property
    def client(self):
        if self._client is None:
            try:
                import chromadb
                from chromadb.config import Settings as ChromaSettings
            except ImportError as exc:
                raise ImportError("Install SpecRAG with the 'chroma' extra to use ChromaDB") from exc
            self.config.persist_directory.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=str(self.config.persist_directory),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
        return self._client

    @property
    def collection(self):
        if self._collection is None:
            metric = self.config.distance_metric
            self._collection = self.client.get_or_create_collection(
                name=self.config.collection_name,
                metadata={
                    "hnsw:space": metric if metric in {"cosine", "l2", "ip"} else "cosine",
                    "model_fingerprint": settings.embedding.fingerprint,
                },
            )
        return self._collection

    def add(self, ids, embeddings, documents=None, metadatas=None) -> None:
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

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

    def update_metadata(self, doc_id: str, new_metadata: dict) -> None:
        current = self.get_metadata(doc_id)
        if not current:
            raise KeyError(doc_id)
        current.update({key: value if isinstance(value, (str, int, float, bool)) else str(value) for key, value in new_metadata.items()})
        self.collection.update(ids=[doc_id], metadatas=[current])

    def get_metadata(self, doc_id: str) -> dict:
        result = self.collection.get(ids=[doc_id], include=["metadatas"])
        return (result.get("metadatas") or [{}])[0] if result.get("ids") else {}

    def get_content(self, doc_id: str) -> str | None:
        result = self.collection.get(ids=[doc_id], include=["documents"])
        return (result.get("documents") or [None])[0] if result.get("ids") else None

    def search_similar(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        threshold: float | None = None,
    ) -> list[dict]:
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        ids = (result.get("ids") or [[]])[0]
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        rows = []
        for doc_id, document, metadata, distance in zip(
            ids,
            documents,
            metadatas,
            distances,
        ):
            similarity = 1 - distance if self.config.distance_metric == "cosine" else 1 / (1 + distance)
            if threshold is None or similarity >= threshold:
                rows.append(
                    {
                        "id": doc_id,
                        "document": document,
                        "metadata": metadata,
                        "distance": distance,
                        "similarity": similarity,
                        "rank": len(rows) + 1,
                    }
                )
        return rows

    def delete(self, ids: list[str]) -> None:
        self.collection.delete(ids=ids)

    def clear(self) -> None:
        self.client.delete_collection(self.config.collection_name)
        self._collection = None

    def count(self) -> int:
        return self.collection.count()

    def get_stats(self) -> dict:
        return {
            "backend": "chromadb",
            "collection_name": self.config.collection_name,
            "count": self.count(),
            "persist_directory": str(self.config.persist_directory),
            "distance_metric": self.config.distance_metric,
            "model_fingerprint": (self.collection.metadata or {}).get("model_fingerprint"),
        }

    def list_documents(self) -> dict[str, str]:
        result = self.collection.get(include=["metadatas"])
        return {
            doc_id: normalize_metadata_paths(metadata or {}).get(
                "source_file",
                "Unknown",
            )
            for doc_id, metadata in zip(
                result.get("ids") or [],
                result.get("metadatas") or [],
            )
        }

    def get_indexed_documents(self) -> tuple[list[str], list[str]]:
        result = self.collection.get(include=["documents"])
        return list(result.get("ids") or []), list(result.get("documents") or [])

    def validate_model(self, model_info: ModelInfo) -> None:
        fingerprint = (self.collection.metadata or {}).get("model_fingerprint")
        if self.count() and not fingerprint:
            raise RuntimeError(
                "Existing collection has no model fingerprint; re-index required"
            )
        if fingerprint and fingerprint != model_info.fingerprint:
            raise RuntimeError("Embedding model fingerprint does not match collection")


_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
