"""
BM25 Search Module for Hybrid Search

This module provides BM25 (Best Matching 25) text search for exact-match ranking.
Used in combination with vector search for hybrid retrieval.
"""

import math
import re
from collections import Counter
from typing import Optional


class BM25Index:
    """
    BM25 index for text-based search.

    BM25 is a bag-of-words retrieval function that ranks documents based on
    the query terms appearing in each document, regardless of their proximity.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Initialize BM25 index.

        Args:
            k1: Term frequency saturation parameter (default 1.5)
            b: Length normalization parameter (default 0.75)
        """
        self.k1 = k1
        self.b = b
        self.doc_ids = []
        self.doc_lengths = []
        self.avg_doc_length = 0
        self.doc_freqs = {}  # term -> number of docs containing term
        self.term_freqs = {}  # doc_idx -> {term: count}
        self.idf = {}  # term -> idf score
        self.N = 0  # total number of documents

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization: lowercase and split on non-alphanumeric."""
        text = text.lower()
        # Keep alphanumeric and some special chars
        tokens = re.findall(r"\b\w+\b", text)
        return tokens

    def build_index(self, doc_ids: list[str], documents: list[str]):
        """
        Build BM25 index from documents.

        Args:
            doc_ids: List of document IDs
            documents: List of document texts
        """
        self.doc_ids = doc_ids
        self.N = len(documents)
        self.doc_freqs = {}
        self.term_freqs = {}
        self.doc_lengths = []

        # First pass: compute term frequencies and document frequencies
        for idx, doc in enumerate(documents):
            tokens = self._tokenize(doc)
            self.doc_lengths.append(len(tokens))

            # Count term frequencies in this document
            tf = Counter(tokens)
            self.term_freqs[idx] = tf

            # Update document frequencies
            for term in tf.keys():
                self.doc_freqs[term] = self.doc_freqs.get(term, 0) + 1

        # Calculate average document length
        self.avg_doc_length = sum(self.doc_lengths) / max(self.N, 1)

        # Calculate IDF for each term
        for term, df in self.doc_freqs.items():
            # IDF formula: log((N - df + 0.5) / (df + 0.5))
            self.idf[term] = math.log((self.N - df + 0.5) / (df + 0.5) + 1)

    def search(self, query: str, top_k: int = 10) -> list[tuple[str, float]]:
        """
        Search for documents matching query.

        Args:
            query: Search query text
            top_k: Number of top results to return

        Returns:
            List of (doc_id, score) tuples sorted by score descending
        """
        query_tokens = self._tokenize(query)
        scores = []

        for idx in range(self.N):
            score = 0.0
            doc_len = self.doc_lengths[idx]
            tf_doc = self.term_freqs[idx]

            for term in query_tokens:
                if term not in self.idf:
                    continue

                tf = tf_doc.get(term, 0)
                if tf == 0:
                    continue

                idf = self.idf[term]

                # BM25 scoring formula
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length)
                score += idf * numerator / denominator

            if score > 0:
                scores.append((self.doc_ids[idx], score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


class HybridSearchEngine:
    """
    Hybrid search engine combining BM25 and vector similarity.

    Uses Reciprocal Rank Fusion (RRF) to combine results from both methods.
    """

    def __init__(self, vector_store, embedding_provider, rrf_k: int = 60):
        """
        Initialize hybrid search engine.

        Args:
            vector_store: Vector store instance
            embedding_provider: Remote text embedding provider
            rrf_k: RRF parameter (default 60)
        """
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
        self.rrf_k = rrf_k
        self.bm25_index = None
        self._index_built = False

    def _ensure_bm25_index(self):
        """Build BM25 index from vector store documents if not already built."""
        if self._index_built:
            return

        doc_ids, documents = self.vector_store.get_indexed_documents()

        if not documents:
            return

        self.bm25_index = BM25Index()
        self.bm25_index.build_index(doc_ids, documents)
        self._index_built = True
        print(f"Built BM25 index with {len(documents)} documents")

    def search(
        self,
        query: str,
        top_k: int = 10,
        vector_weight: float = 0.5,
        bm25_weight: float = 0.5,
        threshold: float | None = None,
        query_embedding: list[float] | None = None,
    ) -> list[dict]:
        """
        Perform hybrid search combining vector and BM25 results.

        Args:
            query: Search query
            top_k: Number of results to return
            vector_weight: Weight for vector search (0-1)
            bm25_weight: Weight for BM25 search (0-1)
            threshold: Optional similarity threshold

        Returns:
            List of search results with combined scores
        """
        self._ensure_bm25_index()

        # Fetch more candidates for fusion
        fetch_k = top_k * 3

        # 1. Vector search
        query_embedding = query_embedding or self.embedding_provider.embed([query])[0]
        vector_results = self.vector_store.search_similar(query_embedding=query_embedding, top_k=fetch_k, threshold=threshold)

        # 2. BM25 search
        bm25_results = []
        if self.bm25_index:
            bm25_results = self.bm25_index.search(query, top_k=fetch_k)

        # 3. Reciprocal Rank Fusion
        rrf_scores = {}

        # Add vector search contributions
        for rank, result in enumerate(vector_results, 1):
            doc_id = result["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + vector_weight / (self.rrf_k + rank)

        # Add BM25 contributions
        for rank, (doc_id, _) in enumerate(bm25_results, 1):
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + bm25_weight / (self.rrf_k + rank)

        # Sort by combined RRF score
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        # Build result list
        results = []
        for rank, doc_id in enumerate(sorted_ids[:top_k], 1):
            # Get original vector result if available for metadata
            vector_result = next((r for r in vector_results if r["id"] == doc_id), None)

            if vector_result:
                results.append(
                    {
                        "id": doc_id,
                        "document": vector_result["document"],
                        "metadata": vector_result["metadata"],
                        "similarity": vector_result["similarity"],
                        "rrf_score": rrf_scores[doc_id],
                        "rank": rank,
                    }
                )
            else:
                # Document only found by BM25, get from store
                content = self.vector_store.get_content(doc_id)
                metadata = self.vector_store.get_metadata(doc_id)
                results.append(
                    {
                        "id": doc_id,
                        "document": content,
                        "metadata": metadata,
                        "similarity": 0.0,  # Not in vector results
                        "rrf_score": rrf_scores[doc_id],
                        "rank": rank,
                    }
                )

        return results

    def invalidate_index(self):
        """Invalidate BM25 index (call after documents change)."""
        self._index_built = False
        self.bm25_index = None
