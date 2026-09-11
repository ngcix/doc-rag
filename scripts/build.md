# Build and deployment

## Local RAG package

```bash
make setup-env
make test
make lint
make build
```

The wheel contains only the RAG application. It does not bundle the embedding
model or ML inference frameworks.

## ONNX model

Follow [`services/embedding/README.md`](../services/embedding/README.md) to
export and validate the model. Model artifacts are intentionally ignored by
Git.

## Containers

```bash
docker compose build
docker compose up
```

Use `compose.dev.yaml` only when the embedding port must be reachable from the
host for benchmarks:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up embedding
```
