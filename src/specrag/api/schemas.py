"""Pydantic request/response schemas for the FastAPI layer."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class SearchMode(str, Enum):
    semantic = "semantic"
    hybrid = "hybrid"
    # lexical reserved — rejected in validator until BM25-only exists


class SearchFilters(BaseModel):
    content_type: Optional[str] = Field(
        default=None,
        description='Set to "image" to return image chunks only',
    )


class SearchRequest(BaseModel):
    query: Optional[str] = None
    queries: Optional[list[str]] = None
    top_k: int = Field(default=5, ge=1, le=100)
    mode: SearchMode = SearchMode.semantic
    filters: Optional[SearchFilters] = None

    @model_validator(mode="after")
    def require_query_or_queries(self):
        has_query = bool(self.query and self.query.strip())
        has_queries = bool(self.queries and any(q.strip() for q in self.queries))
        if not has_query and not has_queries:
            raise ValueError('Provide "query" or a non-empty "queries" list')
        return self


class SearchResultItem(BaseModel):
    rank: int
    document: str
    similarity: float
    metadata: dict[str, Any] = Field(default_factory=dict)
    chunk_id: str


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    latency_ms: float


class DocumentListItem(BaseModel):
    source: str
    chunk_count: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentListItem]
    total: int


class StatsResponse(BaseModel):
    stats: dict[str, Any]


class ChunkResponse(BaseModel):
    chunk_id: str
    metadata: dict[str, Any]
    content_preview: str
    content_length: int


class TagBody(BaseModel):
    tag: str = Field(..., min_length=1)


class TagsResponse(BaseModel):
    chunk_id: str
    original_tags: str = ""
    user_tags: str = ""
    combined_tags: str = ""


class TagMutationResponse(BaseModel):
    status: str = "success"
    chunk_id: str
    tag: Optional[str] = None
    original_tags: str = ""
    user_tags: str = ""
    combined_tags: str = ""
    message: Optional[str] = None


class KnowledgeBody(BaseModel):
    knowledge: str = Field(..., min_length=1)


class KnowledgeResponse(BaseModel):
    chunk_id: str
    knowledge: str
    has_knowledge: bool = True


class HealthResponse(BaseModel):
    status: str


class ReadyResponse(BaseModel):
    status: str
    ready: bool


class ErrorResponse(BaseModel):
    error: str


class NotImplementedResponse(BaseModel):
    error: str
    detail: str = "Not implemented in this phase"
