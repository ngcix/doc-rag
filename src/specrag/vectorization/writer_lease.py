"""Cross-process single-writer lease for a local FAISS volume."""

from __future__ import annotations

import os
from pathlib import Path


class WriterLease:
    """Hold an advisory lock for the lifetime of a writer process."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._descriptor: int | None = None

    def acquire(self) -> None:
        if self._descriptor is not None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self.path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            import fcntl

            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (ImportError, BlockingIOError) as exc:
            os.close(descriptor)
            raise RuntimeError("Another FAISS writer owns this data volume") from exc
        self._descriptor = descriptor

    def release(self) -> None:
        if self._descriptor is None:
            return
        os.close(self._descriptor)
        self._descriptor = None
