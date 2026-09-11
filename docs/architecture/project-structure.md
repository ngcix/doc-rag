# Project structure

```text
spec-rag/
├── compose.yaml
├── compose.dev.yaml
├── pyproject.toml
├── config/
│   └── setting.json
├── services/
│   ├── rag/
│   │   └── Dockerfile
│   └── embedding/
│       ├── Dockerfile
│       ├── export_model.py
│       ├── validate.py
│       └── evaluate_retrieval.py
├── src/specrag/
│   ├── api/
│   ├── cli/
│   ├── embedding/
│   ├── ingestion/
│   ├── search/
│   ├── vectorization/
│   ├── chunking/
│   ├── image_extraction/
│   ├── image_analysis/
│   ├── sequence_chart/
│   └── config/
├── tests/
└── tools/
```

## Dependency direction

- `api` and `cli` call application services in `ingestion` and `ops`.
- Search depends on the `EmbeddingProvider` contract and vector-store methods.
- `embedding/http.py` is the only production adapter that calls the model.
- Vector stores never call the embedding service.
- The embedding container has no dependency on the RAG package or data.

## File size rule

Hand-written Python files target at most 200 lines and must not exceed 300
lines. `tools/check_file_lengths.py` enforces the hard limit in CI.
