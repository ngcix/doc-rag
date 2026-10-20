"""Structure graph: outline parsing, page furniture, references and storage."""

from __future__ import annotations

from types import SimpleNamespace

import pymupdf
import pytest

from specrag.chunking.chunker import DocumentChunker
from specrag.chunking.pdf import strip_page_furniture
from specrag.graph.extract import build_document_graph
from specrag.graph.outline import normalize_key, parse_outline, read_outline, split_heading
from specrag.graph.store import GraphStore
from specrag.ops.graph import _merge_overlapping

PAGES = [
    ("1. Overview", "1. Overview\nThis standard is organized as described in 9.4.2.1 and Annex C."),
    ("9.4.2.1 General", "9.4.2.1 General\nThe Element ID field is defined in Table 9-1.\nTable 9-1—Element IDs\nElement ID 0"),
    ("9.4.2.2 SSID element", "9.4.2.2 SSID element\nThe SSID element uses the format in 9.4.2.1. Width is 5.2 GHz. dot11SSIDLength applies."),
    ("Annex C (normative) MIB", "Annex C (normative) MIB\nSee 9.4.2.2 and Clause 1."),
]


def _write_pdf(path) -> None:
    document = pymupdf.open()
    for page_number, (_, body) in enumerate(PAGES, start=1):
        page = document.new_page()
        page.insert_text((50, 40), "IEEE Std 802.11-2024")
        page.insert_text((50, 55), f"Page {page_number}")
        filler = "\n".join(f"Filler line {line} of page {page_number}." for line in range(30))
        page.insert_text((50, 90), f"{body}\n{filler}")
        page.insert_text((50, 800), "Authorized licensed use limited. Restrictions apply.")
    document.set_toc([[1, title, page] for page, (title, _) in enumerate(PAGES, start=1)])
    document.save(str(path))


def _chunk(chunk_id: str, content: str, clause: str | None, page: int = 1):
    metadata = {"page": page, **({"clause": clause} if clause else {})}
    return SimpleNamespace(chunk_id=chunk_id, content=content, metadata=metadata)


@pytest.mark.parametrize(
    ("heading", "expected"),
    [
        ("9.4.2.1 General", ("9.4.2.1", "General")),
        ("1. Overview", ("1", "Overview")),
        ("Annex C  (normative)  \nASN.1 encoding", ("C", "(normative) ASN.1 encoding")),
        ("C.3 MIB detail", ("C.3", "MIB detail")),
        ("IEEE Std 802.11-2024 Front Cover", None),
        ("Contents", None),
    ],
)
def test_split_heading(heading, expected) -> None:
    assert split_heading(heading) == expected


def test_normalize_key() -> None:
    assert normalize_key("clause 9.4.2.1") == "9.4.2.1"
    assert normalize_key("annex c") == "C"
    assert normalize_key("table  9-277") == "Table 9-277"
    assert normalize_key("Fig. 9-1") == "Figure 9-1"


def test_parse_outline_links_nearest_existing_parent() -> None:
    clauses = parse_outline([[1, "9. Frame formats", 1], [3, "9.4.2 Elements", 2], [5, "9.4.2.1.1 Deep", 3], [1, "Contents", 4]])
    assert [(clause.key, clause.parent) for clause in clauses] == [("9", None), ("9.4.2", "9"), ("9.4.2.1.1", "9.4.2")]


def test_strip_page_furniture_keeps_body_lines() -> None:
    bodies = ["Scope", "Purpose", "Word usage", "Overview", "Annexes"]
    pages = [["IEEE Std 802.11", f"{n}", body, "Footer © IEEE"] for n, body in enumerate(bodies, start=1)]
    assert strip_page_furniture(pages) == bodies


def test_short_documents_keep_every_line() -> None:
    assert strip_page_furniture([["Title", "Body"]]) == ["Title\nBody"]


def test_references_skip_values_headings_and_own_caption() -> None:
    clauses = parse_outline([[1, "1. Overview", 1], [4, "9.4.2.1 General", 2], [4, "9.4.2.2 SSID element", 3]])
    chunks = [
        _chunk("a", "The Element ID field is defined in Table 9-1.\nTable 9-1—Element IDs\n9.4.2.2 SSID element\nfollows", "9.4.2.1"),
        _chunk("b", "Uses 9.4.2.1. Width 5.2 GHz, see 1 and in 1.", "9.4.2.2"),
        _chunk("c", "Table 9-1—Element IDs .......... 12", None),
    ]
    graph = build_document_graph("doc.pdf", clauses, chunks)
    assert graph.edges == {("9.4.2.1", "Table 9-1", "a"), ("9.4.2.2", "9.4.2.1", "b")}
    assert graph.nodes["Table 9-1"] == ("Table 9-1", "table", "Element IDs", 1, "9.4.2.1", "a")


def test_pdf_chunks_carry_page_and_clause(tmp_path) -> None:
    path = tmp_path / "spec.pdf"
    _write_pdf(path)
    chunks = DocumentChunker().chunk_file(path)
    assert not any("Restrictions apply" in chunk.content or "IEEE Std" in chunk.content for chunk in chunks)
    by_clause = {chunk.metadata.get("clause"): chunk.metadata["page"] for chunk in chunks}
    assert by_clause == {"1": 1, "9.4.2.1": 2, "9.4.2.2": 3, "C": 4}


def test_store_round_trip(tmp_path) -> None:
    path = tmp_path / "spec.pdf"
    _write_pdf(path)
    chunks = DocumentChunker().chunk_file(path)
    store = GraphStore(tmp_path / "graph.sqlite")
    store.replace_document(build_document_graph(str(path), read_outline(path), chunks))

    node = store.lookup("9.4.2.1", str(path))
    assert node["title"] == "General"
    assert {row["key"] for row in node["references"]} == {"Table 9-1"}
    assert {row["key"] for row in node["referenced_by"]} == {"1", "9.4.2.2"}
    assert {row["key"] for row in store.walk("C", str(path), "out", 3)} == {"9.4.2.2", "9.4.2.1", "1", "Table 9-1"}
    assert [row["key"] for row in store.find("SSID", "SSID")["nodes"]] == ["9.4.2.2"]
    assert store.find("dot11SSID", "dot11SSID")["terms"][0]["term"] == "dot11SSIDLength"

    store.delete_document(str(path))
    assert store.stats() == {"nodes": 0, "members": 0, "edges": 0, "mentions": 0}


def test_merge_overlapping_chunks() -> None:
    assert _merge_overlapping(["alpha beta gamma", "beta gamma delta", "unrelated"]) == "alpha beta gamma delta\nunrelated"
