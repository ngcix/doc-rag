# Searching

SpecRAG supports semantic search, hybrid search, image-only filtering and
multi-query search.

## CLI

```bash
specrag search "authentication flow"
specrag search -hy "Figure 4.1"
specrag search -pic "state machine diagram"
specrag search -hy -pic "Figure 4.1"
specrag msearch "reconnection" "link loss" "timeout recovery"
```

Search commands print JSON. Unless `--no-save` is passed, results are also
written under `process/output/`.

## REST

```bash
curl -X POST http://localhost:8080/api/v1/search \
  -H "content-type: application/json" \
  -d "{\"query\":\"authentication flow\",\"top_k\":5}"
```

## Choosing a mode

| Need | Use |
| --- | --- |
| Natural-language concept search | `search "query"` |
| Exact figure/table/protocol term lookup | `search -hy "query"` |
| Diagrams, tables or rendered pages | `search -pic "query"` |
| Broad question with multiple phrasings | `msearch "q1" "q2"` |

## Semantic search

Semantic search embeds the query through the configured embedding service and
searches FAISS with cosine similarity.

```text
query -> /v1/embeddings -> 768-dim vector -> FAISS -> ranked results
```

## Hybrid search

Hybrid search combines:

- vector search for semantic similarity,
- BM25 for exact lexical matches,
- reciprocal rank fusion (RRF) to merge rankings.

RRF uses rank instead of raw score, which avoids comparing BM25 scores and
vector similarity scores directly.

```text
RRF_score(doc) = sum(weight / (k + rank))
```

Use hybrid search for figure numbers, table names, exact acronyms and protocol
field names.

## Multi-query search

`msearch` embeds all queries in batches, searches each one, and merges results
with RRF. It is useful for questions that may appear under several terms in a
specification.

```bash
specrag msearch "pairing" "authentication" "security procedure"
```

## Image-only search

`-pic` filters results to rendered PDF/image items. The result metadata includes
the stored image path, source file and page number when available.

```bash
specrag search -pic "connection state machine"
```

This is designed for AI agents with vision capability: search retrieves likely
pages, and the agent inspects the image file to answer.

## Tips

- Start with semantic search for broad questions.
- Use hybrid for exact identifiers.
- Use `-pic` when the answer likely lives in a diagram/table.
- Add tags or knowledge after manually confirming an important result.
