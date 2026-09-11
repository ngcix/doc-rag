#!/usr/bin/env python3
"""Evaluate retrieval quality of an embedding endpoint on a golden dataset."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path

try:
    from .validate import cosine, embed
except ImportError:
    from validate import cosine, embed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--url", default="http://localhost:8081")
    parser.add_argument("--model", default="Alibaba-NLP/gte-multilingual-base")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-recall", type=float, default=0.8)
    parser.add_argument("--min-ndcg", type=float, default=0.8)
    return parser.parse_args()


def _rank(query_vector, document_ids, document_vectors, top_k):
    scored = [(doc_id, cosine(query_vector, vector)) for doc_id, vector in zip(document_ids, document_vectors)]
    scored.sort(key=lambda item: item[1], reverse=True)
    return [doc_id for doc_id, _ in scored[:top_k]]


def _recall(ranked: list[str], relevant: set[str]) -> float:
    return len(set(ranked) & relevant) / max(1, len(relevant))


def _ndcg(ranked: list[str], relevant: set[str]) -> float:
    score = sum(1 / math.log2(index + 2) for index, doc_id in enumerate(ranked) if doc_id in relevant)
    ideal = sum(1 / math.log2(index + 2) for index in range(min(len(relevant), len(ranked))))
    return score / ideal if ideal else 0.0


def main() -> None:
    args = parse_args()
    dataset = json.loads(args.dataset.read_text(encoding="utf-8"))
    documents = dataset["documents"]
    queries = dataset["queries"]
    document_vectors = embed(
        args.url,
        args.model,
        [document["text"] for document in documents],
    )
    query_vectors = embed(
        args.url,
        args.model,
        [query["text"] for query in queries],
    )
    document_ids = [document["id"] for document in documents]
    recalls, ndcgs = [], []
    for query, vector in zip(queries, query_vectors):
        ranked = _rank(vector, document_ids, document_vectors, args.top_k)
        relevant = set(query["relevant_ids"])
        recalls.append(_recall(ranked, relevant))
        ndcgs.append(_ndcg(ranked, relevant))
    recall = statistics.mean(recalls)
    ndcg = statistics.mean(ndcgs)
    print(f"recall_at_{args.top_k}={recall:.6f}")
    print(f"ndcg_at_{args.top_k}={ndcg:.6f}")
    if recall < args.min_recall or ndcg < args.min_ndcg:
        raise SystemExit("Retrieval quality gate failed")


if __name__ == "__main__":
    main()
