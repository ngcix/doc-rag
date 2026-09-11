"""Application-level embedding provider lifecycle."""

from __future__ import annotations

from functools import lru_cache

from specrag.config import settings
from specrag.embedding.base import EmbeddingProvider
from specrag.embedding.http import HttpEmbeddingClient


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    """Return the configured process-wide HTTP provider."""
    return HttpEmbeddingClient(settings.embedding)


def close_embedding_provider() -> None:
    """Close and reset the cached provider."""
    if get_embedding_provider.cache_info().currsize:
        get_embedding_provider().close()
        get_embedding_provider.cache_clear()
