"""Search domain models."""

from __future__ import annotations

from dataclasses import dataclass

from specrag.path_resolver import display_chunk_id, normalize_metadata_paths


@dataclass
class SearchResult:
    rank: int
    document: str
    similarity: float
    metadata: dict
    chunk_id: str

    def __post_init__(self) -> None:
        self.metadata = normalize_metadata_paths(self.metadata)
        self.chunk_id = display_chunk_id(self.chunk_id)

    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "document": self.document,
            "similarity": round(self.similarity, 4),
            "metadata": self.metadata,
            "chunk_id": self.chunk_id,
        }
