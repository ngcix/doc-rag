# Search engine architecture

Search lives in `src/specrag/search/` and depends on two injected boundaries:

- `EmbeddingProvider` from `src/specrag/embedding/`
- vector-store methods from `src/specrag/vectorization/`

The search layer never imports model runtimes.

## Semantic flow

```text
query
  -> EmbeddingProvider.embed([query])
  -> FAISS search_similar(query_embedding)
  -> SearchResult objects
```

FAISS uses `IndexFlatIP` by default. With normalized vectors, inner product is
cosine similarity.

## Hybrid flow

Hybrid search lives in `src/specrag/search/bm25.py`.

```text
query
  -> query embedding -> vector results
  -> tokenized query -> BM25 results
  -> RRF merge -> final ranking
```

RRF avoids mixing raw FAISS and BM25 score scales:

```text
score(doc) = sum(weight / (rrf_k + rank))
```

The default hybrid path uses vector and BM25 rankings from the same FAISS-backed
document collection.

## Multi-query flow

`SearchEngine.search_many` embeds queries in one provider call and searches each
query. Higher-level ops merge multi-query results with RRF.

This reduces HTTP overhead compared with embedding each query separately.

## Result model

`src/specrag/search/results.py` defines the CLI/API-facing result shape:

```text
rank
document
similarity
metadata
chunk_id
```

Metadata may include `source_file`, `page_number`, `type`, `image_path`,
`tags`, `user_tags` and `knowledge` depending on the item.

## Persistence and readiness

Before search, the vector store validates the embedding model fingerprint. If
the configured embedding service does not match the committed index, search
fails instead of silently mixing incompatible vectors.

## Performance notes

Approximate vector storage:

```text
768 dimensions * 4 bytes = about 3 KB per item
```

`Flat` search is exact and simple. It is the right default for small/medium
technical-document corpora. For very large corpora or multiple RAG writers,
move storage to a service such as Qdrant or pgvector rather than scaling local
FAISS writers horizontally.
