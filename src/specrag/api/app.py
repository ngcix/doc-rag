"""FastAPI application factory and lifespan."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from specrag.api.observability import (
    Metrics,
    metrics_response,
    request_observability,
)
from specrag.api.routes import chunks, documents, health, jobs, search

logger = logging.getLogger(__name__)


def _warmup() -> None:
    """Verify the embedding service and prepare the vector store."""
    from specrag.embedding import get_embedding_provider
    from specrag.ops._helpers import get_vector_store

    embedding_provider = get_embedding_provider()
    if not embedding_provider.health():
        raise RuntimeError("Embedding service is not ready")
    store = get_vector_store()
    if hasattr(store, "validate_model"):
        store.validate_model(embedding_provider.model_info())
    # Touch store so FAISS rebuilds from embeddings if needed
    if hasattr(store, "_ensure_index_ready"):
        store._ensure_index_ready()
    elif hasattr(store, "get_stats"):
        store.get_stats()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ready = False
    app.state.write_lock = asyncio.Lock()
    logger.info("Warming up SpecRAG (embedding model + vector store)...")
    try:
        await asyncio.to_thread(_warmup)
        app.state.ready = True
        logger.info("Warmup complete")
    except Exception:
        logger.exception("Warmup failed — /api/v1/ready will report not ready")
        app.state.ready = False
    try:
        yield
    finally:
        from specrag.embedding import close_embedding_provider
        from specrag.vectorization import close_vector_store

        close_embedding_provider()
        close_vector_store()


def create_app() -> FastAPI:
    app = FastAPI(
        title="SpecRAG API",
        version="0.4.0",
        description="Specification ingestion and retrieval API",
        lifespan=lifespan,
    )
    app.state.metrics = Metrics()
    app.middleware("http")(request_observability)
    app.add_api_route("/metrics", metrics_response, methods=["GET"])
    app.include_router(health.router)
    app.include_router(search.router)
    app.include_router(documents.router)
    app.include_router(chunks.router)
    app.include_router(jobs.router)
    return app
