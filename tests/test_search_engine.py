"""Search engine tests with explicit dependencies."""

from __future__ import annotations

from specrag.config import SearchConfig
from specrag.embedding import ModelInfo
from specrag.search.engine import SearchEngine


class StubEmbeddingProvider:
    def embed(self, texts):
        assert texts == ["find me"]
        return [[1.0, 0.0, 0.0]]

    def model_info(self):
        return ModelInfo("stub", "test", 3, "cls", True, 128)


class StubVectorStore:
    def validate_model(self, model):
        return None

    def search_similar(self, query_embedding, top_k, threshold):
        assert query_embedding == [1.0, 0.0, 0.0]
        return [
            {
                "id": "chunk-1",
                "document": "result",
                "similarity": 0.9,
                "metadata": {},
                "rank": 1,
            }
        ]


def test_search_engine_uses_injected_embedding_provider() -> None:
    engine = SearchEngine(
        SearchConfig(top_k=3, score_threshold=0.5),
        embedding_provider=StubEmbeddingProvider(),
        vector_store=StubVectorStore(),
    )

    results = engine.search("find me")

    assert results[0].document == "result"
    assert results[0].similarity == 0.9
