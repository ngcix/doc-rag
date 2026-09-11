"""Cross-process writer lease behavior."""

from __future__ import annotations

import pytest

from specrag.vectorization.writer_lease import WriterLease


def test_writer_lease_rejects_second_owner(tmp_path) -> None:
    lock_path = tmp_path / "store.writer.lock"
    first = WriterLease(lock_path)
    second = WriterLease(lock_path)

    first.acquire()
    try:
        with pytest.raises(RuntimeError, match="Another FAISS writer"):
            second.acquire()
    finally:
        first.release()

    second.acquire()
    second.release()
