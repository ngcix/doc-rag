"""Spreadsheet tables: header-aware record chunks and an exact cell lookup store."""

from __future__ import annotations

import logging
from pathlib import Path

from specrag.tables.store import TableStore

logger = logging.getLogger(__name__)

TABLE_FILE = "tables.sqlite"
SPREADSHEET_EXTENSIONS = (".xlsx", ".csv")


def table_path(vectordb_config=None) -> Path:
    """Stored beside the vector index, like the structure graph, so re-index swaps it too."""
    from specrag.graph import graph_path

    return graph_path(vectordb_config).with_name(TABLE_FILE)


def get_table_store(vectordb_config=None) -> TableStore:
    return TableStore(table_path(vectordb_config))


def spreadsheet_chunks(path: Path) -> list:
    """``SheetChunk`` list for an .xlsx/.csv file: one self-describing chunk per record."""
    from specrag.tables.parse import read_spreadsheet
    from specrag.tables.render import sheet_chunks

    return sheet_chunks(path.name, read_spreadsheet(path))


def index_document_tables(files: list[Path], store: TableStore) -> int:
    """Store the cells of every spreadsheet in ``files``; return how many were stored."""
    from specrag.tables.parse import read_spreadsheet
    from specrag.tables.render import sheet_cells

    stored = 0
    for path in files:
        if path.suffix.lower() not in SPREADSHEET_EXTENSIONS:
            continue
        try:
            store.replace_document(str(path), sheet_cells(read_spreadsheet(path)))
            stored += 1
        except Exception:
            logger.exception("Failed to store table cells for %s", path)
    return stored


__all__ = ["SPREADSHEET_EXTENSIONS", "TABLE_FILE", "TableStore", "get_table_store", "index_document_tables", "spreadsheet_chunks", "table_path"]
