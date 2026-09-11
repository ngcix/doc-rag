# SpecRAG project summary

## Current architecture

SpecRAG is split into two CPU-oriented services:

- Embedding: TEI serving a pinned ONNX export through `/v1/embeddings`.
- RAG: FastAPI/CLI, ingestion, chunking, FAISS/BM25 and metadata operations.

The RAG dependency set contains no model inference frameworks. Search, ingest,
tag updates and knowledge updates share one remote `EmbeddingProvider`
contract.

## Reliability controls

- HTTP connect/read timeouts, bounded concurrency and bounded retries.
- Readiness depends on embedding health.
- Model/index fingerprint compatibility checks.
- Staged whole-index rebuild via `specrag reindex`.
- Thread lock and cross-process single-writer lease for FAISS.
- Atomic temp-file, fsync and rename persistence.
- Request IDs, structured access logs and Prometheus metrics.

## Maintainability controls

- Standard `src`-layout wheel; no Cython or PyInstaller.
- CLI, ingestion, search models/results, document readers, rendering, and
  persistence live in separate modules.
- Every hand-written Python file is limited to 300 lines in CI.
- Unit, contract, ingestion, re-index and quality-metric tests run in CI.

## Deployment constraint

One RAG writer/replica may mount a FAISS volume. The embedding service can be
scaled independently. Horizontal RAG scaling requires an external vector store
such as Qdrant or pgvector.
