"""Structure-graph navigation: clauses, tables, figures and their cross-references."""

from __future__ import annotations

from typing import Any

from specrag.graph import get_graph_store
from specrag.graph.outline import normalize_key
from specrag.ops.errors import NodeNotFoundError, OpsError

MAX_TEXT_CHARS = 20000
_MAX_OVERLAP = 400


def _merge_overlapping(texts: list[str]) -> str:
    """Join consecutive chunks, dropping the overlap the splitter repeated between them."""
    merged = ""
    for text in texts:
        overlap = next(
            (size for size in range(min(_MAX_OVERLAP, len(merged), len(text)), 0, -1) if merged.endswith(text[:size])),
            0,
        )
        merged = f"{merged}{text[overlap:]}" if overlap else f"{merged}\n{text}" if merged else text
    return merged


def _clause_text(chunk_ids: list[str]) -> dict[str, Any]:
    from specrag.ops._helpers import get_vector_store

    store = get_vector_store()
    text = _merge_overlapping([store.get_content(chunk_id) or "" for chunk_id in chunk_ids])
    return {"text": text[:MAX_TEXT_CHARS], "text_truncated": len(text) > MAX_TEXT_CHARS}


def _sources(key: str, source: str | None) -> list[str]:
    sources = get_graph_store().sources(key, source)
    if not sources:
        raise NodeNotFoundError(f"No clause, table or figure '{key}' in the structure graph.")
    return sources


def lookup_node(key: str, source: str | None = None, include_text: bool = False) -> list[dict[str, Any]]:
    """Return the node in every matching document, with parent, children and references."""
    key = normalize_key(key)
    store = get_graph_store()
    results = []
    for document in _sources(key, source):
        node = store.lookup(key, document)
        if include_text:
            node.update(_clause_text(node["chunk_ids"]))
        results.append(node)
    return results


def walk_graph(key: str, source: str | None = None, direction: str = "out", depth: int = 2) -> list[dict[str, Any]]:
    """Follow references outwards ("out") or back to referrers ("in") up to ``depth`` hops."""
    if direction not in {"in", "out"}:
        raise OpsError("direction must be 'in' or 'out'")
    if not 1 <= depth <= 5:
        raise OpsError("depth must be between 1 and 5")
    key = normalize_key(key)
    store = get_graph_store()
    return [{"source": document, "key": key, "direction": direction, "nodes": store.walk(key, document, direction, depth)} for document in _sources(key, source)]


def find_nodes(text: str, source: str | None = None, limit: int = 20) -> dict[str, Any]:
    """Find clauses/tables/figures by title or key, and MIB attributes by name."""
    return get_graph_store().find(text.strip(), normalize_key(text), source, limit)


def graph_stats() -> dict[str, Any]:
    return get_graph_store().stats()
