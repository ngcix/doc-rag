#!/usr/bin/env python3
"""Validate latency and numerical parity of an embedding endpoint."""

from __future__ import annotations

import argparse
import math
import statistics
import time
from pathlib import Path

import httpx

DEFAULT_SAMPLES = [
    "Thiết kế hệ thống phần mềm ổn định.",
    "The service exposes a REST API.",
    "FAISS performs nearest-neighbor search.",
    "Embedding vectors must be normalized.",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-url", default="http://localhost:8081")
    parser.add_argument("--baseline-url")
    parser.add_argument("--model", default="Alibaba-NLP/gte-multilingual-base")
    parser.add_argument("--samples", type=Path)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--min-cosine", type=float, default=0.995)
    parser.add_argument("--expected-dimension", type=int, default=768)
    return parser.parse_args()


def load_samples(path: Path | None) -> list[str]:
    if path is None:
        return DEFAULT_SAMPLES
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def embed(base_url: str, model: str, texts: list[str]) -> list[list[float]]:
    response = httpx.post(
        f"{base_url.rstrip('/')}/v1/embeddings",
        json={"model": model, "input": texts, "encoding_format": "float"},
        timeout=120,
    )
    response.raise_for_status()
    data = sorted(response.json()["data"], key=lambda item: item["index"])
    return [item["embedding"] for item in data]


def cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return dot / (left_norm * right_norm)


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, math.ceil(len(ordered) * fraction) - 1)
    return ordered[index]


def main() -> None:
    args = parse_args()
    samples = load_samples(args.samples)
    latencies = []
    candidate = []
    for _ in range(args.runs):
        started = time.perf_counter()
        candidate = embed(args.candidate_url, args.model, samples)
        latencies.append((time.perf_counter() - started) * 1000)

    dimensions = {len(vector) for vector in candidate}
    if dimensions != {args.expected_dimension}:
        raise SystemExit(f"Unexpected embedding dimensions: {dimensions}")

    norm_errors = [abs(math.sqrt(sum(value * value for value in vector)) - 1.0) for vector in candidate]
    if max(norm_errors) > 0.01:
        raise SystemExit(f"Embeddings are not L2 normalized: max error={max(norm_errors)}")

    print(f"batch={len(samples)} runs={args.runs}")
    print(f"latency_mean_ms={statistics.mean(latencies):.2f}")
    print(f"latency_p95_ms={percentile(latencies, 0.95):.2f}")
    print(f"texts_per_second={len(samples) / (statistics.mean(latencies) / 1000):.2f}")

    if args.baseline_url:
        baseline = embed(args.baseline_url, args.model, samples)
        scores = [cosine(reference, result) for reference, result in zip(baseline, candidate)]
        print(f"parity_cosine_min={min(scores):.6f}")
        print(f"parity_cosine_mean={statistics.mean(scores):.6f}")
        if min(scores) < args.min_cosine:
            raise SystemExit("ONNX parity gate failed")


if __name__ == "__main__":
    main()
