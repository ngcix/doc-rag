"""Document structure graph built from PDF outlines and cross-references."""

from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path

from specrag.graph.store import GraphStore

logger = logging.getLogger(__name__)

GRAPH_FILE = "graph.sqlite"


def graph_path(vectordb_config=None) -> Path:
    """The graph lives beside the vector index so staged re-index swaps both together."""
    from specrag.config import settings

    config = vectordb_config or settings.vectordb
    directory = config.faiss_index_dir if config.backend.lower() == "faiss" else config.persist_directory
    return Path(directory) / GRAPH_FILE


def get_graph_store(vectordb_config=None) -> GraphStore:
    return GraphStore(graph_path(vectordb_config))


def index_document_graphs(files: list[Path], chunks: list, store: GraphStore) -> int:
    """Build and store a graph for every PDF in ``files``; return how many were stored."""
    from specrag.graph.extract import build_document_graph
    from specrag.graph.outline import read_outline

    by_source: dict[str, list] = defaultdict(list)
    for chunk in chunks:
        by_source[str(chunk.source_file)].append(chunk)
    stored = 0
    for path in files:
        if path.suffix.lower() != ".pdf":
            continue
        source = str(path)
        try:
            store.replace_document(build_document_graph(source, read_outline(path), by_source[source]))
            stored += 1
        except Exception:
            logger.exception("Failed to build structure graph for %s", path)
    return stored


__all__ = ["GRAPH_FILE", "GraphStore", "get_graph_store", "graph_path", "index_document_graphs"]
