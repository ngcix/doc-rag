"""FastAPI application factory and lifespan."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from specrag.api.routes import chunks, documents, health, jobs, search

logger = logging.getLogger(__name__)


def _warmup() -> None:
    """Load embedding model and vector store into memory."""
    from specrag.ops._helpers import get_vector_store, get_vectorizer

    vectorizer = get_vectorizer()
    _ = vectorizer.model
    store = get_vector_store()
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
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="SpecRAG API",
        version="0.3.2",
        description="Specification RAG HTTP API (greenfield MVP /api/v1)",
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(search.router)
    app.include_router(documents.router)
    app.include_router(chunks.router)
    app.include_router(jobs.router)
    return app
