# Embedding service

This service owns tokenization, truncation, CLS pooling, L2 normalization, and
ONNX inference. It exposes the OpenAI-compatible `POST /v1/embeddings` endpoint.
The RAG image does not contain Torch, Transformers, Sentence Transformers, or
ONNX Runtime.

## Prepare the model

Create a temporary export environment outside the RAG runtime:

```bash
python -m venv .venv-export
.venv-export/bin/pip install -r services/embedding/requirements-export.txt
.venv-export/bin/python services/embedding/export_model.py \
  --output models/embedding \
  --optimization O3
```

Start with FP32/O3. Export `--quantization avx2` only after it passes the same
quality gates on the deployment CPU. Export writes `specrag-manifest.json` and
`rag.env`; Compose uses the artifact SHA prefix from `rag.env` in the index
fingerprint.

## Validate

Without Docker, compare the exported artifact directly:

```bash
.venv-export/bin/python services/embedding/validate_local.py \
  --artifact models/embedding --output reports/embedding-fp32.json
```

Run the candidate repeatedly:

```bash
python services/embedding/validate.py \
  --candidate-url http://localhost:10001 \
  --expected-dimension 768
```

For numerical parity, run the old Sentence Transformer endpoint separately and
pass `--baseline-url`. The gate checks dimension, L2 norm, minimum cosine,
latency, and throughput. Retrieval evaluation must additionally compare
Recall@K and NDCG@K on the project corpus before cutover.

```bash
python services/embedding/evaluate_retrieval.py \
  tests/data/embedding_golden.json \
  --url http://localhost:10001 --top-k 3
```

## Runtime contract

- Model: `Alibaba-NLP/gte-multilingual-base`
- Pooling: CLS
- Normalization: L2
- Dimension: 768
- Maximum sequence length: 8192
- Runtime: TEI CPU with an exported ONNX artifact

The exact model revision and these vector invariants form the model
fingerprint. A RAG index created by another fingerprint is rejected and must be
rebuilt with `specrag reindex`.
