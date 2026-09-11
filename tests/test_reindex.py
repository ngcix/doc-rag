"""Staged index replacement tests."""

from __future__ import annotations

from specrag.config import settings
from specrag.ingestion import reindex
from specrag.ingestion.service import IngestionReport


def test_reindex_keeps_old_index_until_staging_succeeds(tmp_path, monkeypatch) -> None:
    live = tmp_path / "faiss"
    live.mkdir()
    (live / "old").write_text("old", encoding="utf-8")
    monkeypatch.setattr(settings.vectordb, "faiss_index_dir", live)

    def fake_ingest(*_, vector_store, **__):
        vector_store.config.faiss_index_dir.mkdir(parents=True)
        (vector_store.config.faiss_index_dir / "new").write_text(
            "new",
            encoding="utf-8",
        )
        return IngestionReport(1, 0, 0, 1, 0.1)

    monkeypatch.setattr(reindex, "ingest_documents", fake_ingest)

    report = reindex.rebuild_index(tmp_path)

    assert report.indexed_items == 1
    assert (live / "new").exists()
    assert not (live / "old").exists()


def test_reindex_live_lock_sits_outside_swapped_directory(tmp_path, monkeypatch) -> None:
    live = tmp_path / "faiss"
    live.mkdir()
    monkeypatch.setattr(settings.vectordb, "faiss_index_dir", live)
    lease_paths = []

    class FakeLease:
        def __init__(self, path):
            lease_paths.append(path)

        def acquire(self):
            return None

        def release(self):
            return None

    def fake_ingest(*_, vector_store, **__):
        vector_store.config.faiss_index_dir.mkdir(parents=True)
        (vector_store.config.faiss_index_dir / "new").write_text("new", encoding="utf-8")
        return IngestionReport(1, 0, 0, 1, 0.1)

    monkeypatch.setattr(reindex, "WriterLease", FakeLease)
    monkeypatch.setattr(reindex, "ingest_documents", fake_ingest)

    reindex.rebuild_index(tmp_path)

    assert lease_paths[0].parent == live.parent
    assert lease_paths[0].parent != live
