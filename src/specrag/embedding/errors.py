"""Errors raised by the remote embedding boundary."""


class EmbeddingError(RuntimeError):
    """Base error for embedding failures."""


class EmbeddingUnavailableError(EmbeddingError):
    """The embedding service could not serve the request."""


class EmbeddingContractError(EmbeddingError):
    """The embedding response violates the configured model contract."""
