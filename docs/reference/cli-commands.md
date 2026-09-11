# CLI commands

```bash
specrag <command> [options]
```

The CLI prints JSON for commands that return data or reports.

## Commands

| Command | Purpose |
| --- | --- |
| `process` | Extract, embed and store documents directly into the configured vector store. |
| `reindex` | Build a fresh FAISS index in staging and atomically replace the live index. |
| `search` | Semantic search, optionally hybrid or image-only. |
| `msearch` | Multi-query search with RRF merging. |
| `stats` | Vector-store summary. |
| `init` | Create runtime data directories. |
| `list` | List indexed source documents. |
| `clean` | Remove generated runtime data. |
| `addtag` | Add a user tag and re-embed one item. |
| `listtag` | List original/user/combined tags for one item. |
| `removetag` | Remove a user tag and re-embed one item. |
| `resettags` | Remove all user tags and re-embed one item. |
| `addknowledge` | Append long-form knowledge and re-embed one item. |
| `updateknowledge` | Replace long-form knowledge and re-embed one item. |
| `getknowledge` | Read knowledge for one item. |
| `server` | Start the FastAPI app. |

## process

```bash
specrag process [--input PATH] [-fp] [--format png|jpeg|jpg] [--workers auto|N]
                [--embedding-batch-size N] [--no-charts] [--no-images]
```

Notes:

- `-fp` is required unless `--no-images` is used.
- Embeddings are produced by the configured HTTP embedding service.
- Use `reindex` for production rebuilds.

Examples:

```bash
specrag process -fp
specrag process -fp --format jpeg
specrag process --no-images
specrag process -fp --workers 1 --embedding-batch-size 8
```

## reindex

```bash
specrag reindex [process options] [--yes]
```

Examples:

```bash
specrag reindex -fp -y
docker compose run --rm rag specrag reindex -fp -y
```

## search

```bash
specrag search "query" [--top-k N] [--hybrid] [--pic] [--no-save]
```

Examples:

```bash
specrag search "authentication flow"
specrag search -hy "Figure 4.1"
specrag search -pic "state machine"
specrag search -k 10 --no-save "connection"
```

## msearch

```bash
specrag msearch "query1" "query2" [...] [--top-k N] [--hybrid] [--pic] [--no-save]
```

Examples:

```bash
specrag msearch "reconnection" "link loss" "timeout"
specrag msearch -hy "Figure 4.1" "media payload"
```

## Metadata enrichment

```bash
specrag addtag <doc_id> <tag>
specrag listtag <doc_id>
specrag removetag <doc_id> <tag>
specrag resettags <doc_id>

specrag addknowledge <identifier> <knowledge_text>
specrag updateknowledge <identifier> <knowledge_text>
specrag getknowledge <identifier>
```

`identifier` can be a chunk id or a resolvable image path.

## Runtime and maintenance

```bash
specrag init
specrag stats
specrag list
specrag clean --yes
specrag clean --all --yes
specrag server --host 0.0.0.0 --port 8080
```

API endpoints are mounted under `/api/v1`. OpenAPI is available at `/docs` when
the server is running.
