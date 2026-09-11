# SpecRAG documentation

SpecRAG is a two-service RAG system for technical specifications:

- `embedding`: CPU ONNX/TEI service that exposes `/v1/embeddings`.
- `rag`: FastAPI/CLI service that owns ingestion, FAISS/BM25, metadata and search.

The RAG runtime does not install Torch, Transformers, Sentence Transformers or
ONNX Runtime. Those dependencies are isolated to model export/validation or the
embedding image.

## Start here

| Document | Purpose |
| --- | --- |
| [Installation](./getting-started/installation.md) | Prepare the model artifact, install the RAG package and start Compose. |
| [Quickstart](./getting-started/quickstart.md) | Index documents and run your first search. |
| [Basic workflow](./getting-started/basic-workflow.md) | Daily ingest, search and enrichment flow. |

## User guides

| Document | Purpose |
| --- | --- |
| [Processing](./guides/processing.md) | Document ingestion, image extraction and staged re-indexing. |
| [Searching](./guides/searching.md) | Semantic, hybrid, image-only and multi-query search. |
| [Tagging](./guides/tagging.md) | User tags and re-embedding behavior. |
| [Knowledge](./guides/knowledge.md) | Long-form annotations on chunks/images. |

## Reference

| Document | Purpose |
| --- | --- |
| [CLI commands](./reference/cli-commands.md) | Supported commands and options. |
| [Configuration](./reference/configuration.md) | Runtime settings and environment overrides. |

## Architecture

| Document | Purpose |
| --- | --- |
| [Overview](./architecture/overview.md) | Two-service runtime, data ownership and reliability controls. |
| [Project structure](./architecture/project-structure.md) | Source layout and dependency direction. |
| [Search engine](./architecture/search-engine.md) | FAISS, BM25 and RRF retrieval internals. |
| [Image extraction](./architecture/image-extraction.md) | Full-page PDF image extraction. |

## Development and integrations

| Document | Purpose |
| --- | --- |
| [Dependencies](./development/dependencies.md) | Dependency groups and why model libraries stay out of RAG. |
| [Cline integration](./integrations/cline.md) | How an AI agent should call SpecRAG and enrich results. |
| [Embedding service](../services/embedding/README.md) | Export, validate and benchmark the ONNX model artifact. |

## Maintenance notes

- Use `specrag reindex -fp -y` after changing the embedding fingerprint.
- Use one RAG writer per FAISS data volume.
- Keep generated reports, implementation plans and one-off migration notes out of
  this docs tree unless they are still operationally useful.
