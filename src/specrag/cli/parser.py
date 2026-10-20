"""Command-line parser construction."""

from __future__ import annotations

import argparse
from pathlib import Path

from specrag.config import settings


def _add_search_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--top-k", "-k", type=int, default=5)
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--pic", "-pic", action="store_true")
    parser.add_argument("--hybrid", "-hy", action="store_true")


def _add_process_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--input",
        "-i",
        type=Path,
        default=settings.paths.documents_dir,
    )
    parser.add_argument("--no-charts", action="store_true")
    parser.add_argument("--no-images", action="store_true")
    parser.add_argument("--fullpage", "-fp", action="store_true")
    parser.add_argument(
        "--format",
        "-fmt",
        choices=["png", "jpeg", "jpg"],
        default="png",
    )
    parser.add_argument(
        "--workers",
        "-w",
        default=settings.performance.max_workers,
    )
    parser.add_argument(
        "--embedding-batch-size",
        type=int,
        default=settings.embedding.batch_size,
    )


def _add_document_commands(subparsers) -> None:
    process = subparsers.add_parser("process", help="Process and index documents")
    _add_process_options(process)
    reindex = subparsers.add_parser("reindex", help="Atomically rebuild FAISS index")
    _add_process_options(reindex)
    reindex.add_argument("--yes", "-y", action="store_true")

    clean = subparsers.add_parser("clean", help="Clean generated RAG data")
    clean.add_argument("--all", action="store_true")
    clean.add_argument("--yes", "-y", action="store_true")

    subparsers.add_parser("stats", help="Show vector store statistics")
    subparsers.add_parser("init", help="Initialize data directories")
    subparsers.add_parser("list", help="List indexed documents")


def _add_search_commands(subparsers) -> None:
    search = subparsers.add_parser("search", help="Search indexed documents")
    search.add_argument("query")
    _add_search_options(search)

    multi = subparsers.add_parser("msearch", help="Run multi-query RRF search")
    multi.add_argument("queries", nargs="+")
    _add_search_options(multi)


def _add_metadata_commands(subparsers) -> None:
    add_tag = subparsers.add_parser("addtag")
    add_tag.add_argument("doc_id")
    add_tag.add_argument("tag")

    list_tag = subparsers.add_parser("listtag")
    list_tag.add_argument("doc_id")

    remove_tag = subparsers.add_parser("removetag")
    remove_tag.add_argument("doc_id")
    remove_tag.add_argument("tag")

    reset_tags = subparsers.add_parser("resettags")
    reset_tags.add_argument("doc_id")

    add_knowledge = subparsers.add_parser("addknowledge")
    add_knowledge.add_argument("identifier")
    add_knowledge.add_argument("knowledge")

    update_knowledge = subparsers.add_parser("updateknowledge")
    update_knowledge.add_argument("identifier")
    update_knowledge.add_argument("knowledge")

    get_knowledge = subparsers.add_parser("getknowledge")
    get_knowledge.add_argument("identifier")


def _add_graph_commands(subparsers) -> None:
    clause = subparsers.add_parser("clause", help="Show a clause, table or figure with its references")
    clause.add_argument("key", help='e.g. "9.4.2.1", "Annex C", "Table 9-277"')
    clause.add_argument("--source", "-s", help="Limit to documents whose path contains this text")
    clause.add_argument("--text", "-t", action="store_true", help="Include the node text")

    refs = subparsers.add_parser("refs", help="Follow cross-references from (or to) a node")
    refs.add_argument("key")
    refs.add_argument("--source", "-s")
    refs.add_argument("--in", dest="incoming", action="store_true", help="Show nodes that reference KEY")
    refs.add_argument("--depth", "-d", type=int, default=1)

    find = subparsers.add_parser("find", help="Find clauses/tables/figures by title and MIB attributes by name")
    find.add_argument("text")
    find.add_argument("--source", "-s")
    find.add_argument("--limit", "-k", type=int, default=20)


def _add_table_commands(subparsers) -> None:
    tables = subparsers.add_parser("tables", help="List spreadsheet sheets and their columns")
    tables.add_argument("--source", "-s")

    lookup = subparsers.add_parser("lookup", help="Exact spreadsheet lookup by row and/or column")
    lookup.add_argument("--row", "-r", help='Cell value identifying the row, e.g. "GR"')
    lookup.add_argument("--column", "-c", help='Header level, e.g. "144"')
    lookup.add_argument("--sheet")
    lookup.add_argument("--source", "-s")
    lookup.add_argument("--limit", "-k", type=int, default=200)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="specrag",
        description="SpecRAG document processing and retrieval",
    )
    subparsers = parser.add_subparsers(dest="command")
    _add_document_commands(subparsers)
    _add_search_commands(subparsers)
    _add_metadata_commands(subparsers)
    _add_graph_commands(subparsers)
    _add_table_commands(subparsers)

    server = subparsers.add_parser("server", help="Start the REST API")
    server.add_argument("--host", default="0.0.0.0")
    server.add_argument("--port", type=int, default=8080)
    return parser
