# Configuration

Defaults live in `config/setting.json` and are validated by
`src/specrag/config/settings.py`.

## Paths

| Setting | Purpose |
| --- | --- |
| `paths.database_dir` | Base directory for generated runtime data. |
| `paths.documents_dir` | Default document input directory. |

Relative paths resolve under the repository root. Containers set
`SPECRAG_BASE_DIR=/app`.

Generated data is organized as:

```text
data/documents/
data/extracted_images/
data/faiss_index/
process/input/
process/output/
```

## Embedding

| Setting | Purpose |
| --- | --- |
| `base_url` | Embedding service URL. |
| `model_name` | Served model name sent to `/v1/embeddings`. |
| `model_revision` | Pinned source-model revision. |
| `model_variant` | Export/optimization variant such as `onnx-o3-fp32`. |
| `expected_dimension` | Required vector size. |
| `pooling` | Required pooling mode. |
| `normalize` | Whether returned vectors must be L2-normalized. |
| `max_sequence_length` | Tokenizer truncation limit. |
| `batch_size` | Texts per client request. |
| `connect_timeout_seconds` | HTTP connect timeout. |
| `read_timeout_seconds` | HTTP read/write timeout. |
| `max_retries` | Retries for transport errors and 429/502/503/504. |
| `max_concurrency` | Concurrent embedding requests per RAG process. |

Environment overrides:

```text
EMBEDDING_URL
EMBEDDING_MODEL
EMBEDDING_MODEL_REVISION
EMBEDDING_MODEL_VARIANT
```

## Vector store

| Setting | Purpose |
| --- | --- |
| `vectordb.backend` | `faiss` for the supported deployment path. |
| `vectordb.collection_name` | File prefix and logical collection name. |
| `vectordb.distance_metric` | `cosine` for normalized embeddings. |
| `vectordb.faiss_index_type` | `Flat`, `IVF` or `HNSW`; default is `Flat`. |

FAISS stores the embedding fingerprint with the index:

```text
model_id@revision:variant:pooling:normalization:dimension
```

Changing any fingerprint field requires a full `specrag reindex`.

## Search

| Setting | Purpose |
| --- | --- |
| `top_k` | Default number of results. |
| `score_threshold` | Minimum similarity for semantic results. |
| `include_metadata` | Include metadata in result objects. |

## Processing

| Section | Purpose |
| --- | --- |
| `chunking` | Text chunk size, overlap and separators. |
| `performance` | Worker defaults for extraction/chunking. |
| `image_extraction` | Full-page image selection, render format and context size. |
| `sequence_chart` | Sequence-chart render settings. |

## Compose

`compose.yaml` runs:

- `embedding` on internal port `80`, mounting `./models/embedding:/data:ro`.
- `rag` on public port `8080`, mounting `./data` and `./process`.

`compose.dev.yaml` exposes the embedding service on `127.0.0.1:8081` for local
CLI development.
