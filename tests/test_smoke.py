"""Cheap tests that catch packaging and import regressions."""

from __future__ import annotations

import sys

from fastapi.testclient import TestClient

from specrag.api.app import create_app
from specrag.api.schemas import SearchRequest


def test_app_factory_registers_core_routes() -> None:
    app = create_app()
    paths = set(app.openapi()["paths"])

    assert "/health" in paths
    assert "/api/v1/ready" in paths
    assert "/api/v1/search" in paths


def test_search_request_accepts_single_query() -> None:
    request = SearchRequest(query="architecture")

    assert request.query == "architecture"
    assert request.top_k == 5


def test_rag_import_does_not_load_model_frameworks() -> None:
    assert "torch" not in sys.modules
    assert "transformers" not in sys.modules
    assert "sentence_transformers" not in sys.modules


def test_readiness_is_unavailable_before_warmup() -> None:
    client = TestClient(create_app())
    response = client.get("/api/v1/ready", headers={"x-request-id": "test-id"})

    assert response.status_code == 503
    assert response.json()["ready"] is False
    assert response.headers["x-request-id"] == "test-id"
    assert "specrag_http_requests_total 1" in client.get("/metrics").text
