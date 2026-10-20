"""Render table records as self-describing text chunks and as cells for exact lookup."""

from __future__ import annotations

from dataclasses import dataclass

from specrag.tables.parse import Record, Sheet, Table

MAX_CHUNK_CHARS = 1500
PATH_SEPARATOR = " › "


@dataclass(frozen=True)
class SheetChunk:
    content: str
    metadata: dict


def _prefix(path: tuple[str, ...]) -> tuple[str, ...]:
    """Header levels shared by a run of columns: all but the last two (or last one)."""
    return path[:-2] if len(path) >= 3 else path[:-1] if len(path) == 2 else path


def _groups(columns: list[int], key) -> list[list[int]]:
    """Split ``columns`` into runs of neighbours with the same ``key(column)``."""
    groups: list[list[int]] = []
    previous = object()
    for column in columns:
        current = key(column)
        if groups and current == previous:
            groups[-1].append(column)
        else:
            groups.append([column])
        previous = current
    return groups


def _describe(table: Table, group: list[int], value: str) -> str:
    paths = [table.columns[column] for column in group]
    first = paths[0]
    if len(group) == 1 or len(first) == 1:
        return f"{PATH_SEPARATOR.join(first)}: {value}"
    if len(first) == 2:
        return f"{first[0]}{PATH_SEPARATOR}{', '.join(path[-1] for path in paths)}: {value}"
    head = PATH_SEPARATOR.join(first[:-2])
    span = f"{first[-2]}–{paths[-1][-2]}" if first[-2] != paths[-1][-2] else first[-2]
    return f"{head}{PATH_SEPARATOR}{span}{PATH_SEPARATOR}{', '.join(path[-1] for path in paths)}: {value}"


def record_label(table: Table, record: Record) -> str:
    parts = []
    for group in _groups(table.label_columns, lambda column: table.columns[column]):
        values = [record.cells[column] for column in group if record.cells.get(column)]
        if values:
            parts.append(f"{PATH_SEPARATOR.join(table.columns[group[0]])}: {' / '.join(dict.fromkeys(values))}")
    return " | ".join(parts)


def record_lines(table: Table, record: Record) -> list[str]:
    values = [column for column in table.columns if column not in table.label_columns]
    return [
        _describe(table, group, record.cells[group[0]])
        for group in _groups(values, lambda column: (len(table.columns[column]), _prefix(table.columns[column]), record.cells.get(column, "")))
        if record.cells.get(group[0])
    ]


def _pack(heading: str, lines: list[str], metadata: dict) -> list[SheetChunk]:
    chunks, current = [], [heading]
    for line in lines:
        if len(current) > 1 and sum(map(len, current)) + len(line) > MAX_CHUNK_CHARS:
            chunks.append(SheetChunk("\n".join(current), dict(metadata)))
            current = [heading]
        current.append(line)
    if len(current) > 1 or not chunks:
        chunks.append(SheetChunk("\n".join(current), dict(metadata)))
    return chunks


def sheet_chunks(file_name: str, sheets: list[Sheet]) -> list[SheetChunk]:
    chunks = []
    for sheet in sheets:
        title = f"{file_name}{PATH_SEPARATOR}{sheet.name}"
        for number, table in enumerate(sheet.tables, start=1):
            for record in table.records:
                label = record_label(table, record)
                metadata = {"sheet": sheet.name, "table": number, "row": record.row, "row_label": label}
                chunks.extend(_pack(f"{title}\n{label}", record_lines(table, record), metadata))
        if sheet.notes:
            lines = [f"row {row}: {text}" for row, text in sheet.notes]
            chunks.extend(_pack(f"{title}{PATH_SEPARATOR}notes", lines, {"sheet": sheet.name, "row": sheet.notes[0][0]}))
    return chunks


def sheet_cells(sheets: list[Sheet]) -> list[tuple]:
    """``(sheet, table, row, label, column, value, is_label)`` for every non-empty record cell."""
    cells = []
    for sheet in sheets:
        for number, table in enumerate(sheet.tables, start=1):
            labels = set(table.label_columns)
            for record in table.records:
                label = record_label(table, record)
                for column, value in record.cells.items():
                    path = PATH_SEPARATOR.join(table.columns[column])
                    cells.append((sheet.name, number, record.row, label, path, value, column in labels))
    return cells
