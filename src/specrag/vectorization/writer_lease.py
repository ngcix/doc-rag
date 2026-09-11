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
            self._lock_descriptor(descriptor)
        except OSError as exc:
            os.close(descriptor)
            raise RuntimeError("Another FAISS writer owns this data volume") from exc
        self._descriptor = descriptor

    def _lock_descriptor(self, descriptor: int) -> None:
        if os.name == "nt":
            import msvcrt

            os.lseek(descriptor, 0, os.SEEK_SET)
            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
            return

        import fcntl

        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def release(self) -> None:
        if self._descriptor is None:
            return
        if os.name == "nt":
            import msvcrt

            os.lseek(self._descriptor, 0, os.SEEK_SET)
            msvcrt.locking(self._descriptor, msvcrt.LK_UNLCK, 1)
        os.close(self._descriptor)
        self._descriptor = None
