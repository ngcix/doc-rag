"""PDF text with page boundaries, repeated page furniture removed, and clause positions."""

from __future__ import annotations

import re
from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from specrag.graph.outline import Clause, locate_clauses, parse_outline

PAGE_SEPARATOR = "\n\n"
_TOP_LINES = 6
_BOTTOM_LINES = 3
_MIN_PAGES = 4


@dataclass
class PdfText:
    text: str
    page_starts: list[int]
    clauses: list[Clause] = field(default_factory=list)
    clause_starts: list[int] = field(default_factory=list)

    def page_at(self, offset: int) -> int:
        return bisect_right(self.page_starts, offset)

    def clause_at(self, offset: int) -> Clause | None:
        index = bisect_right(self.clause_starts, offset) - 1
        return self.clauses[index] if index >= 0 else None


def _shape(line: str) -> str:
    return re.sub(r"\d+", "#", line.strip())


def strip_page_furniture(pages: list[list[str]]) -> list[str]:
    """Drop header/footer lines that repeat (digits ignored) on at least half the pages."""
    if len(pages) < _MIN_PAGES:
        return ["\n".join(lines) for lines in pages]
    threshold = len(pages) / 2
    top = Counter(shape for lines in pages for shape in {_shape(line) for line in lines[:_TOP_LINES]})
    bottom = Counter(shape for lines in pages for shape in {_shape(line) for line in lines[-_BOTTOM_LINES:]})
    cleaned = []
    for lines in pages:
        last = len(lines) - _BOTTOM_LINES
        kept = [
            line for index, line in enumerate(lines) if not (index < _TOP_LINES and top[_shape(line)] >= threshold) and not (index >= last and bottom[_shape(line)] >= threshold)
        ]
        cleaned.append("\n".join(kept))
    return cleaned


def read_pdf(path: Path) -> PdfText:
    try:
        import pymupdf
    except ImportError as exc:
        raise ImportError("PyMuPDF is required for PDF processing") from exc
    with pymupdf.open(str(path)) as document:
        pages = strip_page_furniture([page.get_text().splitlines() for page in document])
        toc = document.get_toc()
    page_starts, offset = [], 0
    for page in pages:
        page_starts.append(offset)
        offset += len(page) + len(PAGE_SEPARATOR)
    located = locate_clauses(parse_outline(toc), pages, page_starts)
    return PdfText(
        text=PAGE_SEPARATOR.join(pages),
        page_starts=page_starts,
        clauses=[clause for _, clause in located],
        clause_starts=[start for start, _ in located],
    )


def annotate_chunks(chunks: list, pdf: PdfText) -> None:
    """Add ``page``, ``clause`` and ``clause_title`` to chunk metadata."""
    for chunk in chunks:
        chunk.metadata["page"] = pdf.page_at(chunk.start_index)
        if clause := pdf.clause_at(chunk.start_index):
            chunk.metadata["clause"] = clause.key
            chunk.metadata["clause_title"] = clause.title
