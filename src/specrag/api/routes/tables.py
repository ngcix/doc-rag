"""Spreadsheet table routes: list sheets and exact row/column lookup."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Query

from specrag.ops.errors import OpsError
from specrag.ops.tables import list_tables, lookup_table

router = APIRouter(prefix="/api/v1/tables", tags=["tables"])


@router.get("")
async def tables(source: str | None = None):
    return await asyncio.to_thread(list_tables, source)


@router.get("/lookup")
async def lookup(
    row: str | None = Query(None, description='A cell value identifying the row, e.g. "GR" or "Greece"'),
    column: str | None = Query(None, description='A header level, e.g. "144" or "U-NII-2C"'),
    sheet: str | None = None,
    source: str | None = None,
    limit: int = Query(200, ge=1, le=500),
):
    try:
        return await asyncio.to_thread(lookup_table, row, column, sheet, source, limit)
    except OpsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
