"""Tests for embedding quality metric implementations."""

from services.embedding.evaluate_retrieval import _ndcg, _recall
from services.embedding.validate import cosine, percentile


def test_numerical_parity_metrics() -> None:
    assert cosine([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert percentile([10.0, 20.0, 30.0], 0.95) == 30.0


def test_retrieval_quality_metrics() -> None:
    ranked = ["wrong", "right"]
    relevant = {"right"}

    assert _recall(ranked, relevant) == 1.0
    assert 0.0 < _ndcg(ranked, relevant) < 1.0
