"""Vector store backends used by the RAG service."""

from specrag.vectorization.faiss_store import (
    FaissVectorStore,
    close_faiss_store,
    get_faiss_store,
)
from specrag.vectorization.vector_store import (
    VectorStore,
)
from specrag.vectorization.vector_store import (
    get_vector_store as get_chroma_store,
)


def get_vector_store():
    from specrag.config import settings

    backend = settings.vectordb.backend.lower()
    if backend == "faiss":
        return get_faiss_store()
    if backend == "chromadb":
        return get_chroma_store()
    raise ValueError(f"Unsupported vector backend: {backend}")


def close_vector_store() -> None:
    from specrag.config import settings

    if settings.vectordb.backend.lower() == "faiss":
        close_faiss_store()


__all__ = [
    "FaissVectorStore",
    "VectorStore",
    "close_vector_store",
    "get_chroma_store",
    "get_faiss_store",
    "get_vector_store",
]
