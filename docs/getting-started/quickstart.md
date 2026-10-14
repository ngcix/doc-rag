# Quickstart

This flow assumes the embedding artifact exists in `models/embedding` and the
embedding service is running.

## 1. Add documents

```bash
mkdir -p data/documents
cp /path/to/specs/*.pdf data/documents/
```

Supported source files include `.pdf`, `.docx`, `.md`, `.markdown` and `.txt`.

## 2. Rebuild the index

Use staged re-indexing for the normal cutover path. RAG builds a new FAISS index
in a staging directory and swaps it into place only after extraction, embedding
and persistence succeed.

```bash
docker compose run --rm rag specrag reindex -fp -y
```

For local CLI development:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d embedding

# Windows PowerShell
$env:EMBEDDING_URL="http://localhost:10001"

specrag reindex -fp -y
```

`-fp` enables full-page image extraction for PDF pages that contain diagrams,
tables or figure/table captions.

## 3. Start the API

```bash
docker compose up -d rag
```

Check readiness:

```bash
curl http://localhost:10000/api/v1/ready
```

## 4. Search

REST:

```bash
curl -X POST http://localhost:10000/api/v1/search \
  -H "content-type: application/json" \
  -d "{\"query\":\"authentication flow\",\"top_k\":5}"
```

CLI:

```bash
specrag search "authentication flow"
specrag search -hy "Figure 4.1"
specrag search -pic "state machine diagram"
specrag msearch "reconnect" "link loss" "timeout"
```

CLI output is JSON. Search commands also save result JSON under
`process/output/` unless `--no-save` is passed.

## Useful next commands

| Command | Purpose |
| --- | --- |
| `specrag stats` | Show vector-store summary. |
| `specrag list` | List indexed source documents. |
| `specrag addtag <id> <tag>` | Add a tag and re-embed one chunk. |
| `specrag addknowledge <id> <text>` | Add a longer annotation and re-embed one chunk. |
| `specrag clean --yes` | Remove generated data. |

Next: [Basic workflow](./basic-workflow.md)
