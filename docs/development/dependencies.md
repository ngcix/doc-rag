# Dependencies

SpecRAG keeps model inference dependencies out of the RAG runtime.

## RAG runtime

Defined in `pyproject.toml` and installed by the RAG Docker image.

| Area | Packages | Purpose |
| --- | --- | --- |
| API | `fastapi`, `uvicorn`, `httpx` | REST API and embedding HTTP client. |
| Vector search | `faiss-cpu` | Local nearest-neighbor search. |
| Document readers | `PyMuPDF`, `python-docx`, `python-pptx`, `openpyxl`, `xlrd` | Source document parsing. |
| Chunking | `langchain-text-splitters` | Recursive text splitting. |
| Images | `Pillow` | Rendered image output handling. |
| Config | `pydantic` | Settings validation. |
| Utilities | `tqdm` | Progress reporting. |

The RAG runtime should not depend on:

- `torch`
- `transformers`
- `sentence-transformers`
- `onnxruntime`

Search, ingest, tags and knowledge all call the `EmbeddingProvider` HTTP
boundary instead of importing a local model.

## Embedding export and validation

Defined in `services/embedding/requirements-export.txt`.

| Package | Purpose |
| --- | --- |
| `sentence-transformers[onnx]` | Export and local parity validation for the model artifact. |

This environment is intentionally separate from `.venv` and the RAG image.

## Optional extras

| Extra | Install | Purpose |
| --- | --- | --- |
| `dev` | `pip install -e ".[dev]"` | Tests, Ruff, Pyright and build tooling. |
| `chroma` | `pip install -e ".[chroma]"` | Optional Chroma adapter for experiments. |
| `image-analysis` | `pip install -e ".[image-analysis]"` | Optional Gauss image-analysis script dependencies. |
| `embedding-export` | `pip install -e ".[embedding-export]"` | Alternative way to install export tooling. |

## Development checks

```bash
python -m pytest -q
ruff check src tests services tools scripts
ruff format --check src tests services tools scripts
pyright src
python tools/check_file_lengths.py
```

## Docker split

- `services/rag/Dockerfile` installs only the RAG package.
- `services/embedding/Dockerfile` runs the embedding server over the exported
  model directory.

Keep new dependencies in the smallest layer that needs them. A dependency used
only to prepare or validate the model belongs in the embedding/export path, not
in the RAG runtime.
