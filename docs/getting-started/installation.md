# Installation

## Requirements

- Python 3.10 or newer.
- Docker and Docker Compose for the two-service runtime.
- 4 GB RAM for the embedding container and 2 GB RAM for the RAG container.
- Enough disk for `models/embedding`, `data/` and rendered PDF images.

## 1. Install the RAG package for local development

```bash
git clone <repository-url>
cd spec-rag
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Linux/macOS
source .venv/bin/activate

pip install -e ".[dev]"
```

The RAG package is intentionally lightweight. It contains FAISS, FastAPI,
document readers, chunking and the HTTP embedding client. It does not install
Torch, Transformers, Sentence Transformers or ONNX Runtime.

## 2. Export the embedding artifact

Export is a one-time setup step. The export environment may install model
libraries because it is separate from the RAG runtime.

```bash
python -m venv .venv-export

# Windows PowerShell
.\.venv-export\Scripts\python.exe -m pip install -r services/embedding/requirements-export.txt
.\.venv-export\Scripts\python.exe services/embedding/export_model.py --output models/embedding --optimization O3

# Linux/macOS
.venv-export/bin/pip install -r services/embedding/requirements-export.txt
.venv-export/bin/python services/embedding/export_model.py --output models/embedding --optimization O3
```

The export writes `models/embedding/specrag-manifest.json` and
`models/embedding/rag.env`. Compose loads `rag.env` so RAG can validate the
index fingerprint.

## 3. Start services

```bash
docker compose up --build -d embedding
docker compose up --build -d rag
```

For local CLI work against the containerized embedding service, expose the
embedding port:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d embedding
```

Then point local CLI commands at it:

```bash
# Windows PowerShell
$env:EMBEDDING_URL="http://localhost:8081"

# Linux/macOS
export EMBEDDING_URL=http://localhost:8081
```

## 4. Initialize data directories

```bash
specrag init
```

Runtime data is stored under:

```text
data/
├── documents/          # Source documents to ingest
├── extracted_images/   # Rendered PDF pages
└── faiss_index/        # FAISS index, metadata and embeddings

process/
├── input/
└── output/             # Saved search result JSON when --no-save is not used
```

## Verification

```bash
specrag --help
specrag stats
curl http://localhost:8080/health
curl http://localhost:8080/api/v1/ready
```

`/health` is a liveness check. `/api/v1/ready` is true only after RAG can reach
the embedding service and validate the vector store.

Next: [Quickstart](./quickstart.md)
