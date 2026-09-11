# Basic workflow

SpecRAG has three recurring workflows: ingest, retrieve and enrich.

## 1. Ingest or re-index

Use `reindex` when you want a clean, atomic rebuild of the FAISS store.

```bash
docker compose run --rm rag specrag reindex -fp -y
```

Use `process` only for incremental local work where replacing the whole index is
not required.

```bash
specrag process -fp
```

Both commands call the configured embedding service. If the embedding model
fingerprint changes, rebuild the entire index with `reindex`.

## 2. Retrieve

```bash
specrag search "bluetooth protocol"
specrag search -hy "Figure 4.1"
specrag search -pic "state machine diagram"
specrag msearch "reconnection" "link loss" "timeout"
```

Choose the strategy by intent:

| Intent | Command |
| --- | --- |
| Conceptual question | `search "query"` |
| Exact figure/table/term lookup | `search -hy "query"` |
| Diagram or rendered page lookup | `search -pic "query"` |
| Broad or multi-part question | `msearch "q1" "q2"` |

## 3. Enrich

Tags and knowledge update one chunk/image, call the embedding service for the
new content, and replace that item in FAISS.

```bash
specrag addtag HID_v1.1.1.pdf_p30 "security diagram"
specrag addknowledge HID_v1.1.1.pdf_p30 "This page shows the authentication state machine."
specrag getknowledge HID_v1.1.1.pdf_p30
```

Use enrichment when a person or vision-capable agent has inspected a result and
can add a better description than the raw extracted text.

## Operational checks

```bash
specrag stats
specrag list
curl http://localhost:8080/api/v1/ready
```

Keep one RAG writer per FAISS volume. The embedding service can restart or scale
independently because it owns no RAG data.
