"""Parallel document and image loading helpers."""

from __future__ import annotations

import concurrent.futures
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = (
    ".txt",
    ".md",
    ".pdf",
    ".docx",
    ".markdown",
    ".xlsx",
    ".xls",
    ".pptx",
    ".csv",
)


def discover_documents(input_dir: Path) -> list[Path]:
    files = [path for path in input_dir.rglob("*") if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS]
    return sorted(set(files))


def chunk_documents(files: list[Path], workers: int) -> list:
    from specrag.chunking import chunk_documents as chunk_file

    def load(path: Path) -> list:
        try:
            return chunk_file(path)
        except Exception:
            logger.exception("Failed to chunk %s", path)
            return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        return [chunk for chunks in executor.map(load, files) for chunk in chunks]


def extract_images(pdf_files: list[Path], workers: int, image_format: str) -> list:
    from specrag.image_extraction.extractor import ImageExtractor

    def load(path: Path) -> list:
        try:
            extractor = ImageExtractor(image_format_override=image_format)
            return extractor.extract_from_file(path)
        except Exception:
            logger.exception("Failed to extract images from %s", path)
            return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        return [image for images in executor.map(load, pdf_files) for image in images]
