"""SQLite cell store for exact spreadsheet lookup."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from specrag.tables.render import PATH_SEPARATOR

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cells(
    source TEXT NOT NULL, sheet TEXT NOT NULL, table_no INTEGER NOT NULL, row INTEGER NOT NULL,
    label TEXT NOT NULL, column_path TEXT NOT NULL, value TEXT NOT NULL, is_label INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS cells_row ON cells(source, sheet, table_no, row);
CREATE INDEX IF NOT EXISTS cells_value ON cells(lower(value));
"""
MAX_MATCHES = 500


class TableStore:
    def __init__(self, path: Path):
        self.path = Path(path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            connection.executescript(_SCHEMA)
            with connection:
                yield connection
        finally:
            connection.close()

    def replace_document(self, source: str, cells: list[tuple]) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM cells WHERE source = ?", (source,))
            db.executemany("INSERT INTO cells VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [(source, *cell) for cell in cells])

    def delete_document(self, source: str) -> None:
        if self.path.exists():
            with self._connect() as db:
                db.execute("DELETE FROM cells WHERE source = ?", (source,))

    def sheets(self, source: str | None = None) -> list[dict]:
        if not self.path.exists():
            return []
        with self._connect() as db:
            tables = db.execute(
                """SELECT source, sheet, table_no, COUNT(DISTINCT row) AS rows FROM cells WHERE source LIKE ?
                   GROUP BY source, sheet, table_no ORDER BY source, MIN(rowid)""",
                (f"%{source or ''}%",),
            ).fetchall()
            result = []
            for table in tables:
                columns = db.execute(
                    """SELECT column_path, MAX(is_label) AS is_label FROM cells WHERE source = ? AND sheet = ? AND table_no = ?
                       GROUP BY column_path ORDER BY MIN(rowid)""",
                    (table["source"], table["sheet"], table["table_no"]),
                )
                rows = [dict(row) for row in columns]
                result.append(
                    {
                        **dict(table),
                        "label_columns": [row["column_path"] for row in rows if row["is_label"]],
                        "value_columns": [row["column_path"] for row in rows if not row["is_label"]],
                    }
                )
            return result

    def lookup(
        self,
        row: str | None = None,
        column: str | None = None,
        sheet: str | None = None,
        source: str | None = None,
        limit: int = 200,
    ) -> dict:
        """Cells whose row has a cell equal to ``row`` and whose header path contains ``column``.

        Exact matches win: a row value must equal a cell (case-insensitive) and a column must equal
        one header level. When nothing matches exactly, label cells / header paths are searched for
        the text as a substring.
        """
        if not self.path.exists():
            return {"matches": [], "row_match": None, "column_match": None, "truncated": False}
        limit = min(limit, MAX_MATCHES)
        with self._connect() as db:
            for row_mode in ("exact", "contains") if row else (None,):
                for column_mode in ("exact", "contains") if column else (None,):
                    found = self._query(db, row, row_mode, column, column_mode, sheet, source, limit + 1)
                    if found:
                        return {
                            "matches": found[:limit],
                            "row_match": row_mode,
                            "column_match": column_mode,
                            "truncated": len(found) > limit,
                        }
        return {"matches": [], "row_match": None, "column_match": None, "truncated": False}

    @staticmethod
    def _query(db, row, row_mode, column, column_mode, sheet, source, limit) -> list[dict]:
        clauses = ["c.source LIKE ?", "c.sheet LIKE ?"]
        params: list = [f"%{source or ''}%", f"%{sheet or ''}%"]
        if row_mode:
            match = "lower(k.value) = lower(?)" if row_mode == "exact" else "k.is_label = 1 AND lower(k.value) LIKE lower(?)"
            clauses.append(
                f"""EXISTS (SELECT 1 FROM cells k WHERE k.source = c.source AND k.sheet = c.sheet
                    AND k.table_no = c.table_no AND k.row = c.row AND {match})"""
            )
            params.append(row if row_mode == "exact" else f"%{row}%")
        if column_mode:
            clauses.append("lower(? || c.column_path || ?) LIKE lower(?)")
            pattern = f"%{PATH_SEPARATOR}{column}{PATH_SEPARATOR}%" if column_mode == "exact" else f"%{column}%"
            params.extend([PATH_SEPARATOR, PATH_SEPARATOR, pattern])
        rows = db.execute(
            f"""SELECT c.source, c.sheet, c.table_no, c.row, c.label, c.column_path AS column, c.value FROM cells c
                WHERE {" AND ".join(clauses)} ORDER BY c.source, c.sheet, c.table_no, c.row, c.rowid LIMIT ?""",
            (*params, limit),
        )
        return [dict(found) for found in rows]

    def stats(self) -> dict:
        if not self.path.exists():
            return {"cells": 0}
        with self._connect() as db:
            return {"cells": db.execute("SELECT COUNT(*) FROM cells").fetchone()[0]}
