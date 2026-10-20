"""Exact lookup over spreadsheet tables (sheet / row / column)."""

from __future__ import annotations

from typing import Any

from specrag.ops.errors import OpsError
from specrag.tables import get_table_store


def list_tables(source: str | None = None) -> list[dict[str, Any]]:
    """Sheets and tables with their label and value column header paths."""
    return get_table_store().sheets(source)


def lookup_table(
    row: str | None = None,
    column: str | None = None,
    sheet: str | None = None,
    source: str | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    """Cells for rows identified by ``row`` (e.g. "GR", "Greece") under headers matching ``column`` (e.g. "144")."""
    if not (row or column):
        raise OpsError("Provide row, column, or both.")
    if not 1 <= limit <= 500:
        raise OpsError("limit must be between 1 and 500")
    return get_table_store().lookup(row, column, sheet, source, limit)
