"""CPU thread configuration for embedding workloads."""

from __future__ import annotations

import os
from typing import Optional

from specrag.config import settings


def _is_auto_cpu_value(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in ("", "auto")
    return False


def _coerce_non_negative_int(value, default: int) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, value)


def _coerce_cpu_target(value, default: float = 0.5) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = default
    return min(1.0, max(0.1, value))


def _logical_cpu_count() -> int:
    return max(1, os.cpu_count() or 1)


def _coerce_positive_int(value) -> int | None:
    if value is None:
        return None
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _resolve_cpu_limit(
    value,
    target_cpu_utilization: float | None = None,
    reserved_cpu_threads: int | None = None,
) -> int:
    """Resolve explicit or auto CPU setting to an effective thread count."""
    if not _is_auto_cpu_value(value):
        explicit = _coerce_positive_int(value)
        if explicit:
            return min(explicit, _logical_cpu_count())

    performance = getattr(settings, "performance", None)
    target = _coerce_cpu_target(target_cpu_utilization if target_cpu_utilization is not None else getattr(performance, "target_cpu_utilization", 0.5))
    reserved = _coerce_non_negative_int(
        reserved_cpu_threads if reserved_cpu_threads is not None else getattr(performance, "reserved_cpu_threads", 2),
        default=2,
    )
    logical_cpus = _logical_cpu_count()
    by_target = max(1, int(logical_cpus * target))
    by_reserve = max(1, logical_cpus - reserved)
    return max(1, min(by_target, by_reserve))
