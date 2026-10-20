"""SQLite persistence and queries for document structure graphs."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from specrag.graph.extract import DocumentGraph

_SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes(
    source TEXT NOT NULL, key TEXT NOT NULL, kind TEXT NOT NULL, title TEXT,
    page INTEGER, parent TEXT, chunk_id TEXT, PRIMARY KEY (source, key));
CREATE TABLE IF NOT EXISTS members(chunk_id TEXT PRIMARY KEY, source TEXT NOT NULL, key TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS edges(
    source TEXT NOT NULL, src TEXT NOT NULL, dst TEXT NOT NULL, chunk_id TEXT NOT NULL,
    PRIMARY KEY (source, src, dst, chunk_id));
CREATE TABLE IF NOT EXISTS mentions(source TEXT NOT NULL, term TEXT NOT NULL, chunk_id TEXT NOT NULL,
    PRIMARY KEY (term, chunk_id));
CREATE INDEX IF NOT EXISTS nodes_parent ON nodes(source, parent);
CREATE INDEX IF NOT EXISTS members_key ON members(source, key);
CREATE INDEX IF NOT EXISTS edges_dst ON edges(source, dst);
CREATE INDEX IF NOT EXISTS mentions_source ON mentions(source);
"""
_TABLES = ("nodes", "members", "edges", "mentions")
_LIST_LIMIT = 100


class GraphStore:
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

    def replace_document(self, graph: DocumentGraph) -> None:
        with self._connect() as db:
            self._delete(db, graph.source)
            db.executemany("INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?)", [(graph.source, *node) for node in graph.nodes.values()])
            db.executemany("INSERT OR REPLACE INTO members VALUES (?, ?, ?)", [(chunk, graph.source, key) for chunk, key in graph.members])
            db.executemany("INSERT INTO edges VALUES (?, ?, ?, ?)", [(graph.source, *edge) for edge in graph.edges])
            db.executemany("INSERT OR IGNORE INTO mentions VALUES (?, ?, ?)", [(graph.source, *mention) for mention in graph.mentions])

    def delete_document(self, source: str) -> None:
        if self.path.exists():
            with self._connect() as db:
                self._delete(db, source)

    @staticmethod
    def _delete(db: sqlite3.Connection, source: str) -> None:
        for table in _TABLES:
            db.execute(f"DELETE FROM {table} WHERE source = ?", (source,))

    def sources(self, key: str, source: str | None = None) -> list[str]:
        if not self.path.exists():
            return []
        with self._connect() as db:
            rows = db.execute(
                "SELECT DISTINCT source FROM nodes WHERE key = ? AND source LIKE ? ORDER BY source",
                (key, f"%{source or ''}%"),
            )
            return [row["source"] for row in rows]

    def lookup(self, key: str, source: str) -> dict:
        with self._connect() as db:
            node = dict(db.execute("SELECT * FROM nodes WHERE source = ? AND key = ?", (source, key)).fetchone())
            caption_chunk = node.pop("chunk_id")
            parent = db.execute("SELECT key, title FROM nodes WHERE source = ? AND key = ?", (source, node["parent"])).fetchone()
            children = db.execute("SELECT key, kind, title FROM nodes WHERE source = ? AND parent = ? ORDER BY rowid", (source, key))
            chunk_ids = [row[0] for row in db.execute("SELECT chunk_id FROM members WHERE source = ? AND key = ? ORDER BY rowid", (source, key))]
            if not chunk_ids and caption_chunk:
                chunk_ids = [caption_chunk]
            return {
                **node,
                "parent": dict(parent) if parent else None,
                "children": [dict(row) for row in children],
                "chunk_ids": chunk_ids,
                "references": self._neighbours(db, source, key, "src", "dst"),
                "referenced_by": self._neighbours(db, source, key, "dst", "src"),
            }

    @staticmethod
    def _neighbours(db: sqlite3.Connection, source: str, key: str, here: str, there: str) -> list[dict]:
        rows = db.execute(
            f"""SELECT e.{there} AS key, n.kind, n.title, COUNT(*) AS mentions
                FROM edges e LEFT JOIN nodes n ON n.source = e.source AND n.key = e.{there}
                WHERE e.source = ? AND e.{here} = ? GROUP BY e.{there} ORDER BY mentions DESC, e.{there} LIMIT ?""",
            (source, key, _LIST_LIMIT),
        )
        return [dict(row) for row in rows]

    def walk(self, key: str, source: str, direction: str = "out", depth: int = 2) -> list[dict]:
        here, there = ("src", "dst") if direction == "out" else ("dst", "src")
        with self._connect() as db:
            rows = db.execute(
                f"""WITH RECURSIVE reach(key, depth) AS (
                        SELECT ?, 0
                        UNION
                        SELECT e.{there}, reach.depth + 1 FROM edges e JOIN reach ON e.{here} = reach.key
                        WHERE e.source = ? AND reach.depth < ?)
                    SELECT reach.key, MIN(reach.depth) AS depth, n.kind, n.title, n.page
                    FROM reach LEFT JOIN nodes n ON n.source = ? AND n.key = reach.key
                    WHERE reach.key != ? GROUP BY reach.key ORDER BY depth, reach.key LIMIT ?""",
                (key, source, depth, source, key, _LIST_LIMIT * 5),
            )
            return [dict(row) for row in rows]

    def find(self, text: str, key: str, source: str | None = None, limit: int = 20) -> dict:
        if not self.path.exists():
            return {"nodes": [], "terms": []}
        pattern, scope = f"%{text}%", f"%{source or ''}%"
        with self._connect() as db:
            nodes = db.execute(
                """SELECT source, key, kind, title, page FROM nodes
                   WHERE source LIKE ? AND (key = ? OR title LIKE ?)
                   ORDER BY key != ?, length(title), key LIMIT ?""",
                (scope, key, pattern, key, limit),
            )
            terms = db.execute(
                """SELECT term, source, COUNT(*) AS chunks, MIN(chunk_id) AS sample_chunk_id FROM mentions
                   WHERE source LIKE ? AND term LIKE ? GROUP BY term, source ORDER BY length(term), term LIMIT ?""",
                (scope, pattern, limit),
            )
            return {"nodes": [dict(row) for row in nodes], "terms": [dict(row) for row in terms]}

    def stats(self) -> dict:
        if not self.path.exists():
            return {table: 0 for table in _TABLES}
        with self._connect() as db:
            return {table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in _TABLES}
