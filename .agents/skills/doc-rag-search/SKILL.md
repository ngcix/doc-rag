---
name: doc-rag-search
description: Search indexed documentation and specifications through the SpecRAG REST API. Use when the user asks about content that may be in the indexed documents (specs, requirements, design docs) or asks what documents are available.
---

# Document Search (SpecRAG)

Search the SpecRAG index over HTTP with curl and answer from the returned
chunks, citing the source document for each fact.

## Endpoint

Base URL: `$SPECRAG_URL` if set, otherwise `http://localhost:10000`.

```bash
BASE=${SPECRAG_URL:-http://localhost:10000}
curl -s "$BASE/api/v1/ready"          # {"status":"ok","ready":true} when usable
```

If the service is not ready or unreachable, tell the user rather than guessing.

## Search

`POST /api/v1/search`

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `query` | string | - | Single query. Provide `query` or `queries`. |
| `queries` | string[] | - | Several queries merged with Reciprocal Rank Fusion. |
| `top_k` | int | 5 | 1-100. |
| `mode` | string | `semantic` | `semantic` (meaning) or `hybrid` (BM25 + vector, better for exact terms, IDs, section numbers). |
| `filters.content_type` | string | - | `"image"` returns only rendered page/figure results. |

**Single query:**
```bash
curl -s -X POST "$BASE/api/v1/search" -H "content-type: application/json" \
  -d '{"query": "authentication flow", "top_k": 10}'
```

**Several phrasings for broader coverage:**
```bash
curl -s -X POST "$BASE/api/v1/search" -H "content-type: application/json" \
  -d '{"queries": ["reconnect", "link loss", "timeout handling"], "top_k": 15}'
```

**Exact identifiers (requirement IDs, figure numbers, field names):**
```bash
curl -s -X POST "$BASE/api/v1/search" -H "content-type: application/json" \
  -d '{"query": "Figure 4.1", "mode": "hybrid", "top_k": 10}'
```

## Response

```json
{
  "results": [
    {
      "rank": 1,
      "document": "<full chunk text>",
      "similarity": 0.74,
      "metadata": {
        "source_file": "/app/data/documents/spec.pdf",
        "file_name": "spec.pdf",
        "chunk_index": 12,
        "total_chunks": 136,
        "content_type": "text",
        "page_number": 7
      },
      "chunk_id": "/app/data/documents/spec.pdf_12"
    }
  ],
  "latency_ms": 25.6
}
```

- `document` is the full chunk text; quote from it.
- `metadata.file_name` / `source_file` identify the document to cite;
  `page_number` is present for PDF image results.
- `similarity` is cosine similarity for a single semantic `query`
  (about 0.5-0.8 for relevant matches). For `queries` or `hybrid` it is a
  fusion score (about 0.01-0.05); compare it only within one response.
- An empty `results` list means nothing matched closely enough. Rephrase with
  more specific or alternative terms, or try `hybrid`.

## List indexed documents

```bash
curl -s "$BASE/api/v1/documents"   # {"documents":[{"source": "...", "chunk_count": 136}], "total": 1}
```

Use this when the user asks what is searchable, or to check whether a topic's
source document is indexed at all before concluding it is not covered.

## Workflow

1. Turn the question into 2-4 short technical queries (keywords, synonyms,
   abbreviations and their expansions).
2. Run them together via `queries`; add a `hybrid` search when the question
   names an exact identifier.
3. Read the top chunks, cross-check facts that appear in more than one chunk,
   and answer with citations like `(spec.pdf, chunk 12)`.
4. If results are weak, say what was searched and that the documents may not
   cover it, instead of filling gaps from general knowledge.

## Errors

| Status | Meaning |
|--------|---------|
| 422 | Invalid body, e.g. neither `query` nor `queries`, or `top_k` out of range. |
| 503 | Embedding service unavailable; retry shortly or report it. |
| 500 | Server error; report the `detail` message. |
