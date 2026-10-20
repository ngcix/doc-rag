"""Rule-based structure graph: clause tree, cross-references, captions and MIB terms."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from specrag.graph.outline import Clause, clean

_NUMBER = r"(?:\d{1,2}|[A-Z]{1,2})-\d{1,4}"
_CAPTION = re.compile(rf"^(Table|Figure)\s+({_NUMBER})\s*[—–]\s*(.+?)\s*$", re.M)
_TABLE_FIGURE_REF = re.compile(rf"\b(Table|Figure)\s+({_NUMBER})\b")
_NUMERIC_REF = re.compile(r"(?<![\w.\-/])(\d{1,2}(?:\.\d{1,3}){1,6})(?![\w\-/]|\.\d)")
_ANNEX_SUB_REF = re.compile(r"(?<![\w.\-/])([A-Z]{1,2}(?:\.\d{1,3}){1,5})(?![\w\-/]|\.\d)")
_NAMED_REF = re.compile(r"\b(?:Annex\s+([A-Z]{1,2})|Clause\s+(\d{1,2}))\b")
_CUE = re.compile(r"(?i)\b(?:in|see|per|to|of|and|or|through|subclause|clauses?)\s*,?\s*$")
_UNIT = re.compile(r"\s*(?:[GMk]?Hz|dBm?|[mµμun]s|%|[MG]b/s)\b")
_MIB = re.compile(r"\bdot11[A-Z][A-Za-z0-9]{2,}")
_DOT_LEADER = re.compile(r"\.{4,}|(?:\. ){3,}")


@dataclass
class DocumentGraph:
    source: str
    nodes: dict[str, tuple] = field(default_factory=dict)
    members: list[tuple[str, str]] = field(default_factory=list)
    edges: set[tuple[str, str, str]] = field(default_factory=set)
    mentions: set[tuple[str, str]] = field(default_factory=set)


def _is_heading(text: str, match: re.Match, title: str) -> bool:
    at_line_start = match.start() == 0 or text[match.start() - 1] == "\n"
    following = clean(text[match.end() : match.end() + 80].lstrip(" ."))
    return at_line_start and following.startswith(clean(title)[:20])


def _clause_refs(text: str, titles: dict[str, str], skip: list[tuple[int, int]]) -> set[str]:
    found = set()
    for pattern in (_NUMERIC_REF, _ANNEX_SUB_REF):
        for match in pattern.finditer(text):
            key = match.group(1)
            if key not in titles or any(start <= match.start() < end for start, end in skip):
                continue
            if _is_heading(text, match, titles[key]):
                continue
            if _UNIT.match(text, match.end()):
                continue
            # Short numbers such as "5.2" are often values; demand a cue word before them.
            if key.count(".") < 2 and not _CUE.search(text, max(0, match.start() - 16), match.start()):
                continue
            found.add(key)
    for match in _NAMED_REF.finditer(text):
        key = match.group(1) or match.group(2)
        if key in titles:
            found.add(key)
    return found


def build_document_graph(source: str, clauses: list[Clause], chunks: list) -> DocumentGraph:
    """Build the graph for one document from its outline and annotated chunks."""
    graph = DocumentGraph(source)
    titles = {clause.key: clause.title for clause in clauses}
    for clause in clauses:
        graph.nodes[clause.key] = (clause.key, "clause", clause.title, clause.page, clause.parent, None)

    for chunk in chunks:
        chunk_id, text = chunk.chunk_id, chunk.content
        clause = chunk.metadata.get("clause")
        page = chunk.metadata.get("page")
        if clause:
            graph.members.append((chunk_id, clause))
            node = graph.nodes.get(clause)
            if node and node[5] is None:
                graph.nodes[clause] = (*node[:5], chunk_id)

        captions = []
        for match in _CAPTION.finditer(text):
            captions.append((match.start(), match.end()))
            if _DOT_LEADER.search(match.group(3)):
                continue  # "List of tables/figures" entry, not the caption itself
            key = f"{match.group(1)} {match.group(2)}"
            existing = graph.nodes.get(key)
            if existing is None or (existing[4] is None and clause):
                graph.nodes[key] = (key, match.group(1).lower(), match.group(3), page, clause, chunk_id)

        if clause:
            targets = _clause_refs(text, titles, captions)
            for match in _TABLE_FIGURE_REF.finditer(text):
                if not any(start <= match.start() < end for start, end in captions):
                    targets.add(f"{match.group(1)} {match.group(2)}")
            graph.edges.update((clause, target, chunk_id) for target in targets if target != clause)

        graph.mentions.update((term, chunk_id) for term in set(_MIB.findall(text)))
    return graph
