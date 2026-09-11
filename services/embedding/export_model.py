#!/usr/bin/env python3
"""Export the configured Sentence Transformer to CPU ONNX artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

DEFAULT_MODEL = "Alibaba-NLP/gte-multilingual-base"
DEFAULT_REVISION = "9bbca17d9273fd0d03d5725c7a4b0f6b45142062"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--revision", default=DEFAULT_REVISION)
    parser.add_argument("--output", type=Path, default=Path("models/embedding"))
    parser.add_argument("--optimization", choices=["none", "O1", "O2", "O3"], default="O3")
    parser.add_argument(
        "--quantization",
        choices=["none", "avx2", "avx512", "avx512_vnni"],
        default="none",
    )
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def export(args: argparse.Namespace) -> None:
    from sentence_transformers import (
        SentenceTransformer,
        export_dynamic_quantized_onnx_model,
        export_optimized_onnx_model,
    )

    args.output.mkdir(parents=True, exist_ok=True)
    model = SentenceTransformer(
        args.model,
        revision=args.revision,
        trust_remote_code=True,
        backend="onnx",
        model_kwargs={"export": True},
    )
    model.save_pretrained(args.output)

    artifact = "onnx/model.onnx"
    if args.optimization != "none":
        export_optimized_onnx_model(
            model,
            optimization_config=args.optimization,
            model_name_or_path=str(args.output),
            file_suffix=args.optimization.lower(),
        )
        artifact = f"onnx/model_{args.optimization.lower()}.onnx"
    if args.quantization != "none":
        export_dynamic_quantized_onnx_model(
            model,
            quantization_config=args.quantization,
            model_name_or_path=str(args.output),
            file_suffix=f"int8_{args.quantization}",
        )
        artifact = f"onnx/model_int8_{args.quantization}.onnx"

    selected_artifact = args.output / artifact
    active_artifact = args.output / "onnx" / "model.onnx"
    if selected_artifact != active_artifact:
        shutil.copy2(selected_artifact, active_artifact)
    digest = file_sha256(active_artifact)
    artifact = "onnx/model.onnx"
    dimension = int(model.get_sentence_embedding_dimension())
    if args.quantization != "none":
        variant = f"onnx-int8-{args.quantization}"
    elif args.optimization != "none":
        variant = f"onnx-{args.optimization.lower()}-fp32"
    else:
        variant = "onnx-fp32"
    variant = f"{variant}-{digest[:12]}"
    manifest = {
        "model_id": args.model,
        "revision": args.revision,
        "dimension": dimension,
        "pooling": "cls",
        "normalized": True,
        "max_sequence_length": 8192,
        "artifact": artifact,
        "artifact_sha256": digest,
        "variant": variant,
        "optimization": args.optimization,
        "quantization": args.quantization,
        "fingerprint": (f"{args.model}@{args.revision}:{variant}:cls:l2:{dimension}"),
    }
    (args.output / "specrag-manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    (args.output / "rag.env").write_text(
        f"EMBEDDING_MODEL_VARIANT={variant}\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    export(parse_args())
