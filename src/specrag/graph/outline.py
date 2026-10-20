"""Numbered clauses parsed from a PDF outline (bookmarks)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_ANNEX = re.compile(r"Annex\s+([A-Z]{1,2})\b\s*")
_NUMBERED = re.compile(r"((?:\d{1,2}|[A-Z]{1,2})(?:\.\d{1,3})*)\.?\s+(\S.*)")
_ANNEX_KEY = re.compile(r"[A-Za-z]{1,2}(?:\.\d+)*")
_TABLE_FIGURE = re.compile(r"(?i)(table|figure|fig\.)\s*((?:\d{1,2}|[A-Z]{1,2})-\d{1,4})")


@dataclass(frozen=True)
class Clause:
    key: str
    title: str
    heading: str
    page: int
    parent: str | None


def clean(text: str) -> str:
    return " ".join(text.split())


def split_heading(heading: str) -> tuple[str, str] | None:
    """Return ``(key, title)`` for "9.4.2.1 General", "1. Overview" or "Annex C (normative) ..."."""
    heading = clean(heading)
    if match := _ANNEX.match(heading):
        return match.group(1), heading[match.end() :]
    match = _NUMBERED.fullmatch(heading)
    if not match or not any(char.isdigit() for char in match.group(1)):
        return None
    return match.group(1), match.group(2)


def normalize_key(text: str) -> str:
    """Map user input such as "clause 9.4.2.1", "annex c" or "table 9-277" to a node key."""
    text = clean(text)
    if match := _TABLE_FIGURE.fullmatch(text):
        kind = "Figure" if match.group(1).lower().startswith("fig") else "Table"
        return f"{kind} {match.group(2).upper()}"
    text = re.sub(r"(?i)^(?:sub)?clause\s+|^annex\s+", "", text).rstrip(".")
    return text.upper() if _ANNEX_KEY.fullmatch(text) else text


def _parent(key: str, known: set[str]) -> str | None:
    while "." in key:
        key = key.rsplit(".", 1)[0]
        if key in known:
            return key
    return None


def parse_outline(toc: list) -> list[Clause]:
    """Turn PyMuPDF ``get_toc()`` rows into clauses; unnumbered front matter is skipped."""
    parsed: list[tuple[str, str, str, int]] = []
    seen: set[str] = set()
    for _level, heading, page, *_ in toc:
        if (split := split_heading(heading)) and split[0] not in seen and page > 0:
            seen.add(split[0])
            parsed.append((split[0], split[1], clean(heading), page))
    return [Clause(key, title, heading, page, _parent(key, seen)) for key, title, heading, page in parsed]


def read_outline(path: Path) -> list[Clause]:
    import pymupdf

    with pymupdf.open(str(path)) as document:
        return parse_outline(document.get_toc())


def locate_clauses(clauses: list[Clause], pages: list[str], page_starts: list[int]) -> list[tuple[int, Clause]]:
    """Find each clause heading in its page text; fall back to the page start."""
    located = []
    cursor_page, cursor = 0, 0
    for clause in clauses:
        index = clause.page - 1
        if not 0 <= index < len(pages):
            continue
        start = cursor if index == cursor_page else 0
        pattern = r"\s+".join(map(re.escape, clause.heading.split()))
        match = re.compile(pattern).search(pages[index], start)
        offset = match.start() if match else start
        cursor_page, cursor = index, offset
        located.append((page_starts[index] + offset, clause))
    located.sort(key=lambda item: item[0])
    return located
