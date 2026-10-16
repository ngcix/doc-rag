"""Document ingestion orchestration."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass
from pathlib import Path

from specrag.config import settings
from specrag.embedding import EmbeddingProvider, get_embedding_provider
from specrag.ingestion.loaders import (
    chunk_documents,
    discover_documents,
    extract_images,
)
from specrag.performance import _resolve_cpu_limit
from specrag.vectorization import get_vector_store


@dataclass(frozen=True)
class IngestionReport:
    text_chunks: int
    images: int
    charts: int
    indexed_items: int
    elapsed_seconds: float

    def to_dict(self) -> dict:
        return asdict(self)


def _text_items(chunks: list) -> list[dict]:
    return [
        {
            "chunk_id": chunk.chunk_id,
            "content": chunk.content,
            "metadata": {**chunk.metadata, "content_type": "text"},
            "source_file": chunk.source_file,
        }
        for chunk in chunks
    ]


def _image_items(images: list) -> list[dict]:
    from specrag.image_extraction import get_vectorization_data

    items = get_vectorization_data(images)
    for item in items:
        item.setdefault("metadata", {})["content_type"] = "image"
    return items


def _chart_items(markdown_files: list[Path]) -> list[dict]:
    from specrag.sequence_chart import get_chart_processor

    processor = get_chart_processor()
    items = []
    for markdown in markdown_files:
        charts = processor.process_file(markdown, export_images=True)
        chart_items = processor.get_vectorization_data(charts)
        for item in chart_items:
            item.setdefault("metadata", {})["content_type"] = "chart"
        items.extend(chart_items)
    return items


def _embed_items(provider: EmbeddingProvider, items: list[dict], batch_size: int = 1024) -> None:
    """Embed in slices, keeping float32 arrays instead of a full list of float lists."""
    import numpy as np

    for offset in range(0, len(items), batch_size):
        batch = items[offset : offset + batch_size]
        for item, vector in zip(batch, provider.embed([item["content"] for item in batch])):
            item["embedding"] = np.asarray(vector, dtype=np.float32)


def ingest_documents(
    input_dir: Path | None = None,
    *,
    files: list[Path] | None = None,
    include_charts: bool = True,
    include_images: bool = True,
    image_format: str = "png",
    max_workers: int | str | None = None,
    embedding_batch_size: int | None = None,
    embedding_provider: EmbeddingProvider | None = None,
    vector_store=None,
) -> IngestionReport:
    """Extract, embed, and persist ``files``, or all supported documents in ``input_dir``."""
    started = time.perf_counter()
    if files is None:
        input_dir = Path(input_dir or settings.paths.documents_dir)
        if not input_dir.exists():
            raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
        files = discover_documents(input_dir)

    workers = _resolve_cpu_limit(
        max_workers if max_workers is not None else settings.performance.max_workers,
        target_cpu_utilization=settings.performance.target_cpu_utilization,
        reserved_cpu_threads=settings.performance.reserved_cpu_threads,
    )
    chunks = chunk_documents(files, min(workers, max(1, len(files)))) if files else []
    items = _text_items(chunks)

    images = []
    if include_images:
        pdf_files = [path for path in files if path.suffix.lower() == ".pdf"]
        if pdf_files:
            images = extract_images(
                pdf_files,
                min(workers, len(pdf_files)),
                image_format,
            )
            items.extend(_image_items(images))

    markdown_files = [path for path in files if path.suffix.lower() == ".md"]
    chart_items = _chart_items(markdown_files) if include_charts else []
    items.extend(chart_items)

    if items:
        if embedding_batch_size is not None:
            settings.embedding.batch_size = embedding_batch_size
        provider = embedding_provider or get_embedding_provider()
        store = vector_store or get_vector_store()
        store.validate_model(provider.model_info())
        _embed_items(provider, items)
        store.add_chunks(items)

    return IngestionReport(
        text_chunks=len(chunks),
        images=len(images),
        charts=len(chart_items),
        indexed_items=len(items),
        elapsed_seconds=time.perf_counter() - started,
    )
