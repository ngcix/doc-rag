# Changes

## v0.4.0

- Split SpecRAG into a lightweight RAG runtime and a separate embedding service.
- Add the `EmbeddingProvider` boundary and OpenAI-compatible HTTP embedding
  client.
- Add model fingerprint validation so incompatible FAISS indexes are rejected.
- Add staged `specrag reindex` for whole-index rebuild and cutover.
- Harden FAISS persistence with generation manifests, atomic writes and a
  single-writer lease.
- Add FastAPI health/readiness/metrics endpoints.
- Move CLI parsing and command handlers out of the package entry point.
- Keep Torch, Transformers, Sentence Transformers and ONNX Runtime out of the
  RAG runtime dependency set.
- Add tests for embedding contract, ingestion, search injection, FAISS
  persistence, re-indexing and quality metrics.
- Enforce the 300-line limit for hand-written Python files.

## v0.3.0

- Rename the CLI to `specrag`.
- Normalize project packaging around the `src/specrag` package.
- Add FAISS-backed semantic search and image-aware retrieval workflows.

## v0.2.0

- Add document chunking, PDF image extraction, vector search and CLI workflows.
