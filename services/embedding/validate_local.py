#!/usr/bin/env python3
"""Compare a local ONNX export with the pinned PyTorch baseline."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from export_model import DEFAULT_MODEL, DEFAULT_REVISION
from validate import DEFAULT_SAMPLES, percentile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--revision", default=DEFAULT_REVISION)
    parser.add_argument("--artifact", type=Path, default=Path("models/embedding"))
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--min-cosine", type=float, default=0.995)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def encode(model, samples: list[str]):
    return model.encode(
        samples,
        batch_size=len(samples),
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )


def main() -> None:
    import numpy as np
    from sentence_transformers import SentenceTransformer

    args = parse_args()
    baseline = SentenceTransformer(
        args.model,
        revision=args.revision,
        trust_remote_code=True,
        device="cpu",
    )
    baseline.max_seq_length = 8192
    reference = encode(baseline, DEFAULT_SAMPLES)
    del baseline

    candidate = SentenceTransformer(
        str(args.artifact),
        backend="onnx",
        model_kwargs={"file_name": "onnx/model.onnx"},
        device="cpu",
    )
    candidate.max_seq_length = 8192
    result = encode(candidate, DEFAULT_SAMPLES)
    cosine_scores = np.sum(reference * result, axis=1)
    latencies = []
    for _ in range(args.runs):
        started = time.perf_counter()
        encode(candidate, DEFAULT_SAMPLES)
        latencies.append((time.perf_counter() - started) * 1000)

    manifest = json.loads(
        (args.artifact / "specrag-manifest.json").read_text(encoding="utf-8")
    )
    report = {
        "fingerprint": manifest["fingerprint"],
        "dimension": int(result.shape[1]),
        "parity_cosine_min": float(cosine_scores.min()),
        "parity_cosine_mean": float(cosine_scores.mean()),
        "latency_mean_ms": float(np.mean(latencies)),
        "latency_p95_ms": percentile(latencies, 0.95),
        "texts_per_second": len(DEFAULT_SAMPLES)
        / (float(np.mean(latencies)) / 1000),
    }
    print(json.dumps(report, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if report["dimension"] != 768:
        raise SystemExit("Dimension gate failed")
    if report["parity_cosine_min"] < args.min_cosine:
        raise SystemExit("Numerical parity gate failed")


if __name__ == "__main__":
    main()
