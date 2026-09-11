# Configuration

Defaults are stored in `config/setting.json` and validated by Pydantic models in
`src/specrag/config/settings.py`.

## Embedding

- `base_url`: internal embedding service URL.
- `model_name`: served model name.
- `model_revision`: pinned source model revision.
- `model_variant`: ONNX optimization/quantization variant.
- `expected_dimension`: required vector dimension.
- `pooling`: required pooling method.
- `normalize`: whether vectors are L2 normalized.
- `max_sequence_length`: tokenizer truncation limit.
- `batch_size`: maximum texts per client request.
- `connect_timeout_seconds`, `read_timeout_seconds`: network timeouts.
- `max_retries`: retries for connect, timeout, 429, 502, 503 and 504.
- `max_concurrency`: maximum concurrent requests from one RAG process.

`EMBEDDING_URL`, `EMBEDDING_MODEL`, `EMBEDDING_MODEL_REVISION`, and
`EMBEDDING_MODEL_VARIANT` override JSON values.

## Vector store

FAISS is the default and supports one writer per data volume. ChromaDB is
optional and requires `pip install -e ".[chroma]"`.

An index stores the embedding model fingerprint. Changing model name, revision,
variant, pooling, normalization, or dimension requires `specrag reindex`.

## Paths

Relative paths resolve under the repository root. Containers set
`SPECRAG_BASE_DIR=/app`. `database_dir` contains documents, extracted images,
FAISS and Chroma data.
