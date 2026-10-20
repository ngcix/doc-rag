"""Find tables with (merged, multi-row) headers in spreadsheet grids."""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path

_MIN_FALLBACK_HEADER_CELLS = 3


@dataclass
class Record:
    row: int  # 1-based spreadsheet row
    cells: dict[int, str]  # column index -> value


@dataclass
class Table:
    columns: dict[int, tuple[str, ...]]  # column index -> header path
    label_columns: list[int]
    records: list[Record] = field(default_factory=list)


@dataclass
class Sheet:
    name: str
    tables: list[Table] = field(default_factory=list)
    notes: list[tuple[int, str]] = field(default_factory=list)  # (row, text) outside table records


def format_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    if isinstance(value, datetime) and value.time() == time():
        value = value.date()
    return " ".join(str(value).split())


def _fill_merges(grid: list[list[str]], merges: list[tuple[int, int, int, int]]) -> None:
    for top, bottom, left, right in merges:
        if top >= len(grid) or left >= len(grid[top]):
            continue
        value = grid[top][left]
        for row in range(top, min(bottom, len(grid) - 1) + 1):
            for column in range(left, min(right, len(grid[row]) - 1) + 1):
                grid[row][column] = value


def _table_starts(grid: list[list[str]], merges, assume_header: bool) -> list[tuple[int, int, list[int]]]:
    """Return ``(start_row, header_height, label_columns)``; a start has two or more header merges."""
    vertical = [merge for merge in merges if merge[1] > merge[0]]
    counts = Counter(top for top, *_ in vertical)
    starts = []
    for top in sorted(row for row, count in counts.items() if count >= 2):
        spans = [merge for merge in vertical if merge[0] == top]
        height = max(bottom - top + 1 for _, bottom, _, _ in spans)
        labels = sorted({column for _, _, left, right in spans for column in range(left, right + 1)})
        starts.append((top, height, labels))
    if starts:
        return starts
    for index, row in enumerate(grid):
        filled = [column for column, value in enumerate(row) if value]
        # Count distinct values: a merged title fills many cells with one value.
        if filled and (assume_header or len(set(row) - {""}) >= _MIN_FALLBACK_HEADER_CELLS):
            return [(index, 1, filled)]
    return []


def _header_paths(header: list[list[str]], labels: list[int], width: int) -> dict[int, tuple[str, ...]]:
    """Forward-fill group headers to the right, stopping at empty separator columns."""
    filled = [list(row) for row in header]
    separators = {column for column in range(width) if not any(row[column] for row in header)}
    for level in range(len(header) - 1):
        carry = ""
        for column in range(width):
            if column in labels:
                carry = ""
            elif column in separators and level > 0:
                carry = ""
            elif filled[level][column]:
                carry = filled[level][column]
            else:
                filled[level][column] = carry
    paths = {}
    for column in range(width):
        path: list[str] = []
        for row in filled:
            if row[column] and (not path or path[-1] != row[column]):
                path.append(row[column])
        if path and column not in separators:
            paths[column] = tuple(path)
        elif column in labels:
            paths[column] = (f"column {_letter(column)}",)
    return paths


def _letter(column: int) -> str:
    letters = ""
    column += 1
    while column:
        column, remainder = divmod(column - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def parse_grid(name: str, grid: list[list[str]], merges=(), assume_header: bool = False) -> Sheet:
    """Split a sheet into tables of records plus free-text notes."""
    width = max((len(row) for row in grid), default=0)
    grid = [row + [""] * (width - len(row)) for row in grid]
    merges = list(merges)
    _fill_merges(grid, merges)
    sheet = Sheet(name)
    starts = _table_starts(grid, merges, assume_header)
    boundaries = [start for start, _, _ in starts] + [len(grid)]

    def note(index: int, row: list[str]) -> None:
        text = " | ".join(dict.fromkeys(value for value in row if value))
        # A vertically merged title repeats on every row it spans; keep it once.
        if text and not (sheet.notes and sheet.notes[-1][1] == text):
            sheet.notes.append((index + 1, text))

    for index in range(boundaries[0]):
        note(index, grid[index])
    for (start, height, labels), end in zip(starts, boundaries[1:]):
        columns = _header_paths(grid[start : start + height], labels, width)
        table = Table(columns, [column for column in labels if column in columns])
        # A record fills most row labels; footnotes such as "Note | 1) ISO 3166-1" do not.
        groups = {path: [c for c in table.label_columns if columns[c] == path] for path in dict.fromkeys(columns[c] for c in table.label_columns)}
        needed = len(groups) // 2 + 1
        for index in range(start + height, end):
            row = grid[index]
            if not any(row):
                continue
            # Count distinct values: a footnote merged across the label columns repeats one value.
            values = {next((row[c] for c in members if row[c]), "") for members in groups.values()} - {""}
            if len(values) >= needed:
                table.records.append(Record(index + 1, {column: row[column] for column in columns if row[column]}))
            else:
                note(index, row)
        sheet.tables.append(table)
    return sheet


def read_xlsx(path: Path) -> list[Sheet]:
    import openpyxl

    workbook = openpyxl.load_workbook(str(path), data_only=True)
    try:
        sheets = []
        for worksheet in workbook.worksheets:
            grid = [[format_value(value) for value in row] for row in worksheet.iter_rows(values_only=True)]
            merges = [(r.min_row - 1, r.max_row - 1, r.min_col - 1, r.max_col - 1) for r in worksheet.merged_cells.ranges]
            sheets.append(parse_grid(worksheet.title, grid, merges))
        return sheets
    finally:
        workbook.close()


def read_csv(path: Path) -> list[Sheet]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        grid = [[format_value(value) for value in row] for row in csv.reader(handle)]
    return [parse_grid(path.stem, grid, assume_header=True)]


def read_spreadsheet(path: Path) -> list[Sheet]:
    return read_csv(path) if path.suffix.lower() == ".csv" else read_xlsx(path)
