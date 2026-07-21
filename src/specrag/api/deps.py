"""Shared FastAPI dependencies."""

from __future__ import annotations

import asyncio
from typing import Annotated

from fastapi import Request


def get_write_lock(request: Request) -> asyncio.Lock:
    return request.app.state.write_lock


WriteLock = Annotated[asyncio.Lock, ...]
