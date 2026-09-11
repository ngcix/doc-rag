"""OpenAI-compatible HTTP embedding client."""

from __future__ import annotations

import threading
import time
import math
from collections.abc import Sequence
from typing import Any

import httpx

from specrag.config import EmbeddingConfig
from specrag.embedding.base import ModelInfo
from specrag.embedding.errors import (
    EmbeddingContractError,
    EmbeddingUnavailableError,
)

_RETRYABLE_STATUS_CODES = {429, 502, 503, 504}


class HttpEmbeddingClient:
    """Call a remote embedding service with bounded retries and validation."""

    def __init__(
        self,
        config: EmbeddingConfig,
        client: httpx.Client | None = None,
    ) -> None:
        self.config = config
        self._owns_client = client is None
        self._semaphore = threading.BoundedSemaphore(config.max_concurrency)
        self._client = client or httpx.Client(
            base_url=config.base_url.rstrip("/"),
            timeout=httpx.Timeout(
                connect=config.connect_timeout_seconds,
                read=config.read_timeout_seconds,
                write=config.read_timeout_seconds,
                pool=config.connect_timeout_seconds,
            ),
            limits=httpx.Limits(
                max_connections=config.max_concurrency,
                max_keepalive_connections=config.max_concurrency,
            ),
        )

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        inputs = list(texts)
        if not inputs:
            return []
        if any(not isinstance(text, str) or not text.strip() for text in inputs):
            raise ValueError("Embedding inputs must be non-empty strings")

        embeddings: list[list[float]] = []
        for offset in range(0, len(inputs), self.config.batch_size):
            embeddings.extend(self._embed_batch(inputs[offset : offset + self.config.batch_size]))
        return embeddings

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = self._request(
            "POST",
            "/v1/embeddings",
            json={
                "model": self.config.model_name,
                "input": texts,
                "encoding_format": "float",
            },
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise EmbeddingContractError("Embedding response is not JSON") from exc
        return self._parse_embeddings(payload, len(texts))

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        with self._semaphore:
            return self._request_with_retries(method, path, **kwargs)

    def _request_with_retries(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        last_error: Exception | None = None
        attempts = self.config.max_retries + 1

        for attempt in range(attempts):
            try:
                response = self._client.request(method, path, **kwargs)
                if response.status_code not in _RETRYABLE_STATUS_CODES:
                    response.raise_for_status()
                    return response
                last_error = EmbeddingUnavailableError(f"Embedding service returned HTTP {response.status_code}")
            except httpx.TransportError as exc:
                last_error = exc
            except httpx.HTTPStatusError as exc:
                raise EmbeddingContractError(f"Embedding request rejected: HTTP {exc.response.status_code}") from exc

            if attempt + 1 < attempts:
                time.sleep(0.1 * (2**attempt))

        raise EmbeddingUnavailableError("Embedding service unavailable") from last_error

    def _parse_embeddings(
        self,
        payload: dict[str, Any],
        expected_count: int,
    ) -> list[list[float]]:
        response_model = payload.get("model")
        if response_model and response_model != self.config.model_name:
            raise EmbeddingContractError(f"Expected model {self.config.model_name}, received {response_model}")
        data = payload.get("data")
        if not isinstance(data, list) or len(data) != expected_count:
            raise EmbeddingContractError(f"Expected {expected_count} embeddings, received {len(data) if isinstance(data, list) else 'invalid data'}")

        try:
            ordered = sorted(data, key=lambda item: item["index"])
            if [item["index"] for item in ordered] != list(range(expected_count)):
                raise EmbeddingContractError(
                    "Embedding response indices do not match input order"
                )
            vectors = [[float(value) for value in item["embedding"]] for item in ordered]
        except (KeyError, TypeError, ValueError) as exc:
            raise EmbeddingContractError("Malformed embedding response") from exc

        for vector in vectors:
            if len(vector) != self.config.expected_dimension:
                raise EmbeddingContractError(f"Expected dimension {self.config.expected_dimension}, received {len(vector)}")
            if not all(math.isfinite(value) for value in vector):
                raise EmbeddingContractError("Embedding contains a non-finite value")
            if self.config.normalize:
                norm = math.sqrt(sum(value * value for value in vector))
                if not 0.98 <= norm <= 1.02:
                    raise EmbeddingContractError(
                        f"Embedding is not L2 normalized (norm={norm:.4f})"
                    )
        return vectors

    def health(self) -> bool:
        try:
            self._request("GET", "/health")
            return True
        except (EmbeddingUnavailableError, EmbeddingContractError):
            return False

    def model_info(self) -> ModelInfo:
        return ModelInfo(
            model_id=self.config.model_name,
            revision=self.config.model_revision,
            dimension=self.config.expected_dimension,
            pooling=self.config.pooling,
            normalized=self.config.normalize,
            max_sequence_length=self.config.max_sequence_length,
            variant=self.config.model_variant,
        )

    def close(self) -> None:
        if self._owns_client:
            self._client.close()
