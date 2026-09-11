"""Ingestion service tests."""

from __future__ import annotations

from types import SimpleNamespace

from specrag.embedding import ModelInfo
from specrag.ingestion import service


class Provider:
    def model_info(self):
        return ModelInfo("model", "revision", 3, "cls", True, 128)

    def embed(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]


class Store:
    def __init__(self):
        self.validated = None
        self.chunks = None

    def validate_model(self, model):
        self.validated = model

    def add_chunks(self, chunks):
        self.chunks = chunks


def test_ingestion_embeds_before_single_store_write(tmp_path, monkeypatch) -> None:
    document = tmp_path / "sample.txt"
    document.write_text("sample", encoding="utf-8")
    chunk = SimpleNamespace(
        chunk_id="sample-1",
        content="sample",
        metadata={},
        source_file=str(document),
    )
    monkeypatch.setattr(service, "discover_documents", lambda _: [document])
    monkeypatch.setattr(service, "chunk_documents", lambda *_: [chunk])
    store = Store()

    report = service.ingest_documents(
        tmp_path,
        include_images=False,
        include_charts=False,
        embedding_provider=Provider(),
        vector_store=store,
    )

    assert report.indexed_items == 1
    assert store.validated.dimension == 3
    assert store.chunks[0]["embedding"] == [1.0, 0.0, 0.0]
