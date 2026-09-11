"""Semantic search orchestration."""

from __future__ import annotations

from typing import Optional

from specrag.config import SearchConfig, ensure_directories, settings
from specrag.search.models import SearchResult
from specrag.search.results import format_results, save_results


class SearchEngine:
    def __init__(
        self,
        config: SearchConfig | None = None,
        embedding_provider=None,
        vector_store=None,
    ):
        self.config = config or settings.search
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store
        ensure_directories()

    @property
    def embedding_provider(self):
        if self._embedding_provider is None:
            from specrag.embedding import get_embedding_provider

            self._embedding_provider = get_embedding_provider()
        return self._embedding_provider

    @property
    def vector_store(self):
        if self._vector_store is None:
            from specrag.vectorization import get_vector_store

            self._vector_store = get_vector_store()
        return self._vector_store

    def search(
        self,
        query: str,
        top_k: int | None = None,
        threshold: float | None = None,
        filter_metadata: dict | None = None,
        query_embedding: list[float] | None = None,
    ) -> list[SearchResult]:
        del filter_metadata  # Reserved until store backends share filter semantics.
        top_k = top_k or self.config.top_k
        threshold = threshold if threshold is not None else self.config.score_threshold
        self.vector_store.validate_model(self.embedding_provider.model_info())
        embedding = query_embedding or self.embedding_provider.embed([query])[0]
        rows = self.vector_store.search_similar(
            query_embedding=embedding,
            top_k=top_k,
            threshold=threshold,
        )
        return [
            SearchResult(
                rank=row["rank"],
                document=row["document"],
                similarity=row["similarity"],
                metadata=row["metadata"],
                chunk_id=row["id"],
            )
            for row in rows
        ]

    def save_search_results(
        self,
        query: str,
        results: list[SearchResult],
        query_id: str | None = None,
        extra_params: dict | None = None,
    ):
        return save_results(query, results, query_id, extra_params)

    def search_and_save(
        self,
        query: str,
        query_id: str | None = None,
        **kwargs,
    ) -> list[SearchResult]:
        results = self.search(query, **kwargs)
        self.save_search_results(query, results, query_id, kwargs)
        return results

    def batch_search(self, queries: list[str], **kwargs):
        embeddings = self.embedding_provider.embed(queries)
        return {query: self.search(query, query_embedding=embedding, **kwargs) for query, embedding in zip(queries, embeddings)}

    def format_results(
        self,
        results: list[SearchResult],
        format_type: str = "text",
    ) -> str:
        return format_results(results, format_type)


_search_engine: SearchEngine | None = None


def get_search_engine() -> SearchEngine:
    global _search_engine
    if _search_engine is None:
        _search_engine = SearchEngine()
    return _search_engine


def search(query: str, **kwargs) -> list[SearchResult]:
    return get_search_engine().search(query, **kwargs)
