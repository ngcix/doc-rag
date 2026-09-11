"""Embedding service contract used by the RAG application."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ModelInfo:
    """Identity and vector invariants of an embedding model."""

    model_id: str
    revision: str
    dimension: int
    pooling: str
    normalized: bool
    max_sequence_length: int
    variant: str = "onnx-o3-fp32"

    @property
    def fingerprint(self) -> str:
        normalization = "l2" if self.normalized else "none"
        return f"{self.model_id}@{self.revision}:{self.variant}:{self.pooling}:{normalization}:{self.dimension}"


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Text-to-vector provider independent of its transport/runtime."""

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed texts while preserving input order."""
        ...

    def health(self) -> bool:
        """Return whether the provider can accept inference requests."""
        ...

    def model_info(self) -> ModelInfo:
        """Return the active model contract."""
        ...

    def close(self) -> None:
        """Release network or runtime resources."""
        ...
