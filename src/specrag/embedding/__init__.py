"""Remote embedding boundary."""

from specrag.embedding.base import EmbeddingProvider, ModelInfo
from specrag.embedding.errors import (
    EmbeddingContractError,
    EmbeddingError,
    EmbeddingUnavailableError,
)
from specrag.embedding.factory import (
    close_embedding_provider,
    get_embedding_provider,
)
from specrag.embedding.http import HttpEmbeddingClient

__all__ = [
    "EmbeddingContractError",
    "EmbeddingError",
    "EmbeddingProvider",
    "EmbeddingUnavailableError",
    "HttpEmbeddingClient",
    "ModelInfo",
    "close_embedding_provider",
    "get_embedding_provider",
]
