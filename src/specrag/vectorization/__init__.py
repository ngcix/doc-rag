"""Vectorization module."""


def get_vectorizer():
    from .vectorizer import get_vectorizer as _get_vectorizer
    return _get_vectorizer()


def vectorize_text(*args, **kwargs):
    from .vectorizer import vectorize_text as _vectorize_text
    return _vectorize_text(*args, **kwargs)


def get_vector_store():
    """
    Get the vector store based on configured backend.
    
    Returns:
        VectorStore or FaissVectorStore based on settings.vectordb.backend
    """
    from specrag.config import settings

    backend = settings.vectordb.backend.lower()
    
    if backend == "faiss":
        from .faiss_store import get_faiss_store
        return get_faiss_store()
    if backend == "chromadb":
        from .vector_store import get_vector_store as get_chroma_store
        return get_chroma_store()

    print(f"Unknown backend '{backend}', defaulting to FAISS")
    from .faiss_store import get_faiss_store
    return get_faiss_store()


def get_chroma_store():
    from .vector_store import get_vector_store as _get_chroma_store
    return _get_chroma_store()


def get_faiss_store():
    from .faiss_store import get_faiss_store as _get_faiss_store
    return _get_faiss_store()


def __getattr__(name: str):
    if name == "TextVectorizer":
        from .vectorizer import TextVectorizer
        return TextVectorizer
    if name == "VectorStore":
        from .vector_store import VectorStore
        return VectorStore
    if name == "FaissVectorStore":
        from .faiss_store import FaissVectorStore
        return FaissVectorStore
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "TextVectorizer",
    "get_vectorizer",
    "vectorize_text",
    "VectorStore",
    "FaissVectorStore",
    "get_vector_store",
    "get_chroma_store",
    "get_faiss_store",
]
