"""FAISS metadata and model compatibility tests without loading FAISS."""

from __future__ import annotations

import pytest

from specrag.config import VectorDBConfig
from specrag.embedding import ModelInfo
from specrag.vectorization import faiss_persistence
from specrag.vectorization.faiss_store import FaissVectorStore
from specrag.vectorization.persistence import atomic_write_json


def _model(revision: str = "one") -> ModelInfo:
    return ModelInfo("model", revision, 3, "cls", True, 128)


def test_empty_store_accepts_and_records_model_contract(tmp_path) -> None:
    store = FaissVectorStore(VectorDBConfig(faiss_index_dir=tmp_path))

    store.validate_model(_model())

    assert store._model_fingerprint == _model().fingerprint


def test_store_rejects_different_model_fingerprint(tmp_path) -> None:
    store = FaissVectorStore(VectorDBConfig(faiss_index_dir=tmp_path))
    store._model_fingerprint = _model("one").fingerprint

    with pytest.raises(RuntimeError, match="fingerprint"):
        store.validate_model(_model("two"))


def test_atomic_json_write_leaves_complete_document(tmp_path) -> None:
    target = tmp_path / "summary.json"

    atomic_write_json(target, {"count": 2})

    assert target.read_text(encoding="utf-8").strip().endswith("}")
    assert not list(tmp_path.glob("*.tmp"))


def test_faiss_store_round_trip(tmp_path) -> None:
    config = VectorDBConfig(faiss_index_dir=tmp_path)
    store = FaissVectorStore(config)
    store.validate_model(_model())
    store.add(
        ids=["one", "two"],
        embeddings=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        documents=["first", "second"],
        metadatas=[{"source_file": "a"}, {"source_file": "b"}],
    )
    store.close()

    reopened = FaissVectorStore(config)
    reopened.validate_model(_model())
    results = reopened.search_similar([1.0, 0.0, 0.0], top_k=1)
    reopened.close()

    assert results[0]["id"] == "one"
    assert results[0]["similarity"] == pytest.approx(1.0)


def test_failed_generation_keeps_previous_committed_store(
    tmp_path,
    monkeypatch,
) -> None:
    config = VectorDBConfig(faiss_index_dir=tmp_path)
    store = FaissVectorStore(config)
    store.validate_model(_model())
    store.add(["one"], [[1.0, 0.0, 0.0]], ["old"], [{}])
    original_write = faiss_persistence.atomic_write_pickle
    calls = 0

    def fail_second_write(path, payload):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("disk full")
        original_write(path, payload)

    monkeypatch.setattr(faiss_persistence, "atomic_write_pickle", fail_second_write)
    with pytest.raises(OSError, match="disk full"):
        store.replace("one", [0.0, 1.0, 0.0], "new", {})
    assert store.get_content("one") == "old"
    store.close()

    reopened = FaissVectorStore(config)
    assert reopened.get_content("one") == "old"
    reopened.close()
