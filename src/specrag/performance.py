"""CPU thread configuration for embedding workloads."""
from __future__ import annotations

import os
from typing import Optional

from specrag.config import settings

_threads_configured = False


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


def _coerce_positive_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        value = int(value)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _resolve_cpu_limit(
    value,
    target_cpu_utilization: Optional[float] = None,
    reserved_cpu_threads: Optional[int] = None,
) -> int:
    """Resolve explicit or auto CPU setting to an effective thread count."""
    if not _is_auto_cpu_value(value):
        explicit = _coerce_positive_int(value)
        if explicit:
            return min(explicit, _logical_cpu_count())

    performance = getattr(settings, "performance", None)
    target = _coerce_cpu_target(
        target_cpu_utilization
        if target_cpu_utilization is not None
        else getattr(performance, "target_cpu_utilization", 0.5)
    )
    reserved = _coerce_non_negative_int(
        reserved_cpu_threads
        if reserved_cpu_threads is not None
        else getattr(performance, "reserved_cpu_threads", 2),
        default=2,
    )
    logical_cpus = _logical_cpu_count()
    by_target = max(1, int(logical_cpus * target))
    by_reserve = max(1, logical_cpus - reserved)
    return max(1, min(by_target, by_reserve))


def _set_thread_env(thread_count: int) -> None:
    """Set CPU thread env vars before heavy libraries initialize."""
    thread_count = max(1, int(thread_count))
    for env_name in (
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    ):
        os.environ[env_name] = str(thread_count)


def configure_embedding_threads(
    embedding_threads=None,
    *,
    thread_count: Optional[int] = None,
    target_cpu_utilization: Optional[float] = None,
    reserved_cpu_threads: Optional[int] = None,
) -> int:
    """Configure CPU threads once before loading embedding backends."""
    global _threads_configured

    if thread_count is None:
        thread_count = _resolve_cpu_limit(
            embedding_threads
            if embedding_threads is not None
            else getattr(getattr(settings, "performance", None), "embedding_threads", None),
            target_cpu_utilization=target_cpu_utilization,
            reserved_cpu_threads=reserved_cpu_threads,
        )

    if not _threads_configured:
        _set_thread_env(thread_count)
        _threads_configured = True

    try:
        import torch

        torch.set_num_threads(thread_count)
        torch.set_num_interop_threads(max(1, min(2, thread_count)))
    except Exception:
        pass

    return thread_count
