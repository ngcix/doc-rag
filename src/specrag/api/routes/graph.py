"""Structure-graph routes: clause lookup, reference walks and title search."""

from __future__ import annotations

import asyncio
from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from specrag.ops import find_nodes, graph_stats, lookup_node, walk_graph
from specrag.ops.errors import NodeNotFoundError, OpsError

router = APIRouter(prefix="/api/v1/graph", tags=["graph"])


async def _call(function, *args):
    try:
        return await asyncio.to_thread(function, *args)
    except NodeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OpsError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/node")
async def read_node(
    key: str = Query(..., description='Clause, table or figure, e.g. "9.4.2.1", "Annex C", "Table 9-277"'),
    source: str | None = None,
    text: bool = False,
):
    return await _call(lookup_node, key, source, text)


@router.get("/walk")
async def walk(
    key: str,
    source: str | None = None,
    direction: Literal["in", "out"] = "out",
    depth: int = Query(1, ge=1, le=5),
):
    return await _call(walk_graph, key, source, direction, depth)


@router.get("/find")
async def find(q: str, source: str | None = None, limit: int = Query(20, ge=1, le=200)):
    return await _call(find_nodes, q, source, limit)


@router.get("/stats")
async def stats():
    return await _call(graph_stats)
