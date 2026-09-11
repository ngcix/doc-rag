"""Search result persistence and presentation."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from specrag.config import PROCESS_INPUT_DIR, PROCESS_OUTPUT_DIR
from specrag.search.models import SearchResult


def save_results(
    query: str,
    results: list[SearchResult],
    query_id: str | None = None,
    extra_params: dict | None = None,
) -> Path:
    timestamp = datetime.now().isoformat()
    query_id = query_id or f"query_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    input_file = PROCESS_INPUT_DIR / f"{query_id}.json"
    output_file = PROCESS_OUTPUT_DIR / f"{query_id}.json"
    input_file.write_text(
        json.dumps(
            {
                "query_id": query_id,
                "query": query,
                "timestamp": timestamp,
                "parameters": extra_params or {},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    output_file.write_text(
        json.dumps(
            {
                "query_id": query_id,
                "query": query,
                "timestamp": timestamp,
                "result_count": len(results),
                "results": [result.to_dict() for result in results],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return output_file


def format_results(results: list[SearchResult], format_type: str = "text") -> str:
    if not results:
        return "No results found."
    if format_type == "json":
        return json.dumps(
            [result.to_dict() for result in results],
            ensure_ascii=False,
            indent=2,
        )
    if format_type == "markdown":
        sections = ["# Search Results"]
        for result in results:
            sections.extend(
                [
                    f"## Result {result.rank} (Similarity: {result.similarity:.4f})",
                    f"**Source:** {result.metadata.get('source_file', 'Unknown')}",
                    f"```\n{result.document}\n```",
                ]
            )
        return "\n\n".join(sections)
    lines = [f"Found {len(results)} results:"]
    for result in results:
        lines.extend(
            [
                f"[{result.rank}] Score: {result.similarity:.4f}",
                f"    ID: {result.chunk_id}",
                f"    Source: {result.metadata.get('source_file', 'Unknown')}",
                f"    Content: {result.document[:200]}...",
                "",
            ]
        )
    return "\n".join(lines)
