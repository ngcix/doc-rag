"""Upload, delete, job, and UI route tests."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from specrag import ops
from specrag.api.app import create_app
from specrag.api.routes import documents as documents_routes
from specrag.config import settings
from specrag.ingestion import service
from specrag.ingestion.service import IngestionReport
from specrag.ops import documents as documents_ops


class FakeStore:
    def __init__(self, sources: dict[str, str]):
        self.sources = dict(sources)

    def list_documents(self):
        return dict(self.sources)

    def delete(self, ids):
        for chunk_id in ids:
            self.sources.pop(chunk_id, None)


@pytest.fixture
def documents_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings.paths, "documents_dir", tmp_path)
    return tmp_path


def _wait(client: TestClient, job_id: str) -> dict:
    for _ in range(100):
        job = client.get(f"/api/v1/jobs/{job_id}").json()
        if job["finished_at"]:
            return job
        time.sleep(0.02)
    raise AssertionError("job did not finish")


def test_upload_saves_file_and_runs_ingest_job(documents_dir, monkeypatch) -> None:
    ingested = []
    monkeypatch.setattr(documents_routes, "ingest_file", lambda path: ingested.append(path) or {"indexed_items": 3})
    client = TestClient(create_app())

    response = client.post("/api/v1/documents/upload", files={"file": ("../spec.md", b"# Spec")})

    assert response.status_code == 202
    job = _wait(client, response.json()["id"])
    assert job["status"] == "succeeded"
    assert job["result"] == {"indexed_items": 3}
    assert ingested == [(documents_dir / "spec.md").resolve()]
    assert (documents_dir / "spec.md").read_bytes() == b"# Spec"
    assert [path.name for path in documents_dir.iterdir()] == ["spec.md"]


def test_upload_rejects_unsupported_type(documents_dir) -> None:
    response = TestClient(create_app()).post("/api/v1/documents/upload", files={"file": ("tool.exe", b"x")})

    assert response.status_code == 400
    assert not any(documents_dir.iterdir())


def test_failed_job_reports_error(documents_dir, monkeypatch) -> None:
    def boom(path):
        raise RuntimeError("embedding down")

    monkeypatch.setattr(documents_routes, "ingest_file", boom)
    client = TestClient(create_app())

    job_id = client.post("/api/v1/documents/upload", files={"file": ("a.txt", b"a")}).json()["id"]

    job = _wait(client, job_id)
    assert job["status"] == "failed"
    assert job["error"] == "embedding down"
    assert client.get("/api/v1/jobs").json()["jobs"][0]["id"] == job_id


def test_delete_route_runs_delete_job(monkeypatch) -> None:
    monkeypatch.setattr(documents_routes, "delete_document", lambda source: {"source": source, "deleted_chunks": 2})
    client = TestClient(create_app())

    response = client.delete("/api/v1/documents", params={"source": "/docs/a b.pdf"})

    assert response.status_code == 202
    assert _wait(client, response.json()["id"])["result"] == {"source": "/docs/a b.pdf", "deleted_chunks": 2}


def test_unknown_job_is_404() -> None:
    assert TestClient(create_app()).get("/api/v1/jobs/missing").status_code == 404


def test_ui_is_served_and_root_redirects() -> None:
    client = TestClient(create_app())

    assert "SpecRAG" in client.get("/ui/").text
    assert client.get("/", follow_redirects=False).headers["location"] == "/ui/"


def test_delete_document_removes_chunks_and_file(documents_dir, monkeypatch) -> None:
    document = documents_dir / "a.txt"
    document.write_text("a")
    source = str(document.resolve())
    store = FakeStore({f"{source}_0": source, f"{source}_1": source, "other_0": "/elsewhere/b.txt"})
    monkeypatch.setattr(documents_ops, "get_vector_store", lambda: store)

    result = ops.delete_document(source)

    assert result == {"source": source, "deleted_chunks": 2, "file_deleted": True}
    assert store.sources == {"other_0": "/elsewhere/b.txt"}
    assert not document.exists()


def test_delete_document_never_deletes_files_outside_documents_dir(documents_dir, tmp_path_factory, monkeypatch) -> None:
    outside = tmp_path_factory.mktemp("outside") / "keep.txt"
    outside.write_text("keep")
    monkeypatch.setattr(documents_ops, "get_vector_store", lambda: FakeStore({}))

    with pytest.raises(ops.DocumentNotFoundError):
        ops.delete_document(str(outside))
    assert outside.exists()


def test_ingest_file_replaces_previous_version_chunks(tmp_path, monkeypatch) -> None:
    document = tmp_path / "a.txt"
    document.write_text("short now")
    source = str(document.resolve())
    store = FakeStore({f"{source}_0": source, f"{source}_1": source, f"{source}_2": source, "other_0": "/b.txt"})
    monkeypatch.setattr(documents_ops, "get_vector_store", lambda: store)

    def fake_ingest(*, files, vector_store):
        assert files == [document.resolve()]
        vector_store.sources[f"{source}_0"] = source
        return IngestionReport(1, 0, 0, 1, 0.1)

    monkeypatch.setattr("specrag.ingestion.ingest_documents", fake_ingest)

    result = ops.ingest_file(document)

    assert store.sources == {f"{source}_0": source, "other_0": "/b.txt"}
    assert result["replaced_chunks"] == 3
    assert result["indexed_items"] == 1


def test_ingest_documents_with_files_skips_discovery(tmp_path, monkeypatch) -> None:
    document = tmp_path / "only.txt"
    chunked = []

    def no_discovery(_):
        raise AssertionError("discover_documents should not run")

    monkeypatch.setattr(service, "discover_documents", no_discovery)
    monkeypatch.setattr(service, "chunk_documents", lambda files, _: chunked.extend(files) or [])

    report = service.ingest_documents(files=[document], include_images=False, include_charts=False)

    assert chunked == [document]
    assert report.indexed_items == 0
