# SpecRAG

SpecRAG indexes technical specifications for semantic, hybrid and image-aware
retrieval. It is designed for AI agents that need to search long PDF/spec
collections, inspect returned diagrams, and enrich the index over time.

## Runtime shape

SpecRAG runs as two services:

- `embedding`: CPU ONNX/TEI service exposing OpenAI-compatible
  `POST /v1/embeddings`.
- `rag`: FastAPI/CLI service for ingestion, FAISS/BM25 search, metadata,
  tags and knowledge.

The RAG runtime does not install Torch, Transformers, Sentence Transformers or
ONNX Runtime. Model export and validation live under `services/embedding/`.

## Features

| Feature | Purpose |
| --- | --- |
| Semantic search | Retrieve by meaning using FAISS over normalized embeddings. |
| Hybrid search | Combine BM25 exact matching and vector search with RRF. |
| Full-page image extraction | Render PDF pages with diagrams/tables and return image paths. |
| Tags and knowledge | Re-embed verified annotations to improve future retrieval. |
| Staged re-index | Build a fresh FAISS store and atomically swap it into place. |
| API and CLI | Use `specrag` locally or FastAPI on port `8080`. |

## Quickstart

```bash
git clone <repository-url>
cd spec-rag

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Export the embedding artifact:

```bash
python -m venv .venv-export
.\.venv-export\Scripts\python.exe -m pip install -r services/embedding/requirements-export.txt
.\.venv-export\Scripts\python.exe services/embedding/export_model.py --output models/embedding --optimization O3
```

Start services and build the index:

```bash
docker compose up --build -d embedding
docker compose run --rm rag specrag reindex -fp -y
docker compose up -d rag
```

Search over REST:

```bash
curl -X POST http://localhost:8080/api/v1/search ^
  -H "content-type: application/json" ^
  -d "{\"query\":\"authentication flow\",\"top_k\":5}"
```

Search with the CLI:

```bash
specrag search "authentication flow"
specrag search -hy "Figure 4.1"
specrag search -pic "state machine diagram"
specrag msearch "reconnect" "link loss" "timeout"
```

For local CLI work against the containerized embedding service:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d embedding
$env:EMBEDDING_URL="http://localhost:8081"
```

## Core commands

| Command | Purpose |
| --- | --- |
| `specrag reindex -fp -y` | Staged full rebuild of the FAISS index. |
| `specrag process -fp` | Direct processing for local iteration. |
| `specrag search "query"` | Semantic search. |
| `specrag search -hy "query"` | Hybrid BM25 + vector search. |
| `specrag search -pic "query"` | Image/rendered-page results only. |
| `specrag addtag <id> <tag>` | Add a tag and re-embed one item. |
| `specrag addknowledge <id> <text>` | Add longer annotation and re-embed one item. |
| `specrag stats` | Vector-store summary. |

## Project layout

```text
spec-rag/
├── compose.yaml
├── config/
├── docs/
├── services/
│   ├── rag/
│   └── embedding/
├── src/specrag/
│   ├── api/
│   ├── cli/
│   ├── embedding/
│   ├── ingestion/
│   ├── search/
│   └── vectorization/
├── tests/
└── tools/
```

## Documentation

| Topic | Link |
| --- | --- |
| Documentation index | [docs/README.md](docs/README.md) |
| Installation | [docs/getting-started/installation.md](docs/getting-started/installation.md) |
| Quickstart | [docs/getting-started/quickstart.md](docs/getting-started/quickstart.md) |
| CLI reference | [docs/reference/cli-commands.md](docs/reference/cli-commands.md) |
| Configuration | [docs/reference/configuration.md](docs/reference/configuration.md) |
| Architecture | [docs/architecture/overview.md](docs/architecture/overview.md) |
| Embedding service | [services/embedding/README.md](services/embedding/README.md) |

## Development

```bash
python -m pytest -q
ruff check src tests services tools scripts
ruff format --check src tests services tools scripts
pyright src
python tools/check_file_lengths.py
```

Hand-written Python files must stay under 300 lines.
