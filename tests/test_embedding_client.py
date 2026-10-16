"""Contract tests for the remote embedding boundary."""

from __future__ import annotations

import httpx
import pytest

from specrag.config import EmbeddingConfig
from specrag.embedding import EmbeddingContractError, HttpEmbeddingClient


def _config(**overrides) -> EmbeddingConfig:
    values = {
        "base_url": "http://embedding.test",
        "expected_dimension": 3,
        "batch_size": 2,
        "max_retries": 0,
    }
    values.update(overrides)
    return EmbeddingConfig(**values)


def test_embed_batches_and_preserves_response_order() -> None:
    batch_sizes: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = __import__("json").loads(request.content)
        batch_sizes.append(len(body["input"]))
        data = [
            {
                "index": index,
                "embedding": ([1.0, 0.0, 0.0] if index == 0 else [0.0, 1.0, 0.0]),
            }
            for index in reversed(range(len(body["input"])))
        ]
        return httpx.Response(200, json={"data": data})

    transport = httpx.MockTransport(handler)
    raw_client = httpx.Client(
        transport=transport,
        base_url="http://embedding.test",
    )
    client = HttpEmbeddingClient(_config(), raw_client)

    vectors = client.embed(["one", "two", "three"])

    assert batch_sizes == [2, 1]
    assert vectors == [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [1.0, 0.0, 0.0],
    ]


def test_embed_rejects_dimension_mismatch() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            json={"data": [{"index": 0, "embedding": [1.0, 2.0]}]},
        )
    )
    raw_client = httpx.Client(
        transport=transport,
        base_url="http://embedding.test",
    )
    client = HttpEmbeddingClient(_config(), raw_client)

    with pytest.raises(EmbeddingContractError, match="Expected dimension 3"):
        client.embed(["one"])


def test_embed_rejects_non_normalized_vectors() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            json={"data": [{"index": 0, "embedding": [2.0, 0.0, 0.0]}]},
        )
    )
    raw_client = httpx.Client(
        transport=transport,
        base_url="http://embedding.test",
    )
    client = HttpEmbeddingClient(_config(), raw_client)

    with pytest.raises(EmbeddingContractError, match="not L2 normalized"):
        client.embed(["one"])


@pytest.mark.parametrize(
    ("overrides", "reported", "ok"),
    [
        ({}, "Alibaba-NLP/gte-multilingual-base", True),
        ({}, "/data", False),
        ({"served_model_name": "/data"}, "/data", True),
        ({"served_model_name": "/data"}, "other", False),
    ],
)
def test_embed_checks_served_model_name(overrides, reported, ok) -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            json={"model": reported, "data": [{"index": 0, "embedding": [1.0, 0.0, 0.0]}]},
        )
    )
    raw_client = httpx.Client(transport=transport, base_url="http://embedding.test")
    client = HttpEmbeddingClient(_config(**overrides), raw_client)

    if ok:
        assert client.embed(["one"]) == [[1.0, 0.0, 0.0]]
    else:
        with pytest.raises(EmbeddingContractError, match="Expected model"):
            client.embed(["one"])


def test_model_fingerprint_captures_vector_invariants() -> None:
    client = HttpEmbeddingClient(_config())

    assert client.model_info().fingerprint.endswith(":cls:l2:3")

    client.close()


def test_retryable_service_error_is_retried() -> None:
    attempts = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(503)
        return httpx.Response(
            200,
            json={"data": [{"index": 0, "embedding": [1.0, 0.0, 0.0]}]},
        )

    raw_client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://embedding.test",
    )
    client = HttpEmbeddingClient(_config(max_retries=1), raw_client)

    assert client.embed(["one"]) == [[1.0, 0.0, 0.0]]
    assert attempts == 2
