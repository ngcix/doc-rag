"""Search module."""


def __getattr__(name: str):
    if name in {"SearchEngine", "SearchResult", "get_search_engine", "search"}:
        from .engine import SearchEngine, SearchResult, get_search_engine, search
        return {
            "SearchEngine": SearchEngine,
            "SearchResult": SearchResult,
            "get_search_engine": get_search_engine,
            "search": search,
        }[name]
    if name in {"BM25Index", "HybridSearchEngine"}:
        from .bm25 import BM25Index, HybridSearchEngine
        return {
            "BM25Index": BM25Index,
            "HybridSearchEngine": HybridSearchEngine,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "SearchEngine",
    "SearchResult",
    "get_search_engine",
    "search",
    "BM25Index",
    "HybridSearchEngine",
]
