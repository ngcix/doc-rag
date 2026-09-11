# Cline integration

SpecRAG works well with a vision-capable coding agent such as Cline. The agent
uses SpecRAG for retrieval, inspects returned image paths when needed, and then
optionally enriches the index with tags or knowledge.

## Preconditions

- The embedding service is running.
- Documents have been indexed with `specrag reindex -fp -y` or
  `specrag process -fp`.
- Cline can read files under `data/extracted_images/` when image results are
  returned.

## Retrieval workflow

```text
user question
  -> choose search strategy
  -> run specrag search/msearch or call POST /api/v1/search
  -> inspect JSON results
  -> read image_path files for visual answers
  -> answer with citations/metadata
```

Recommended commands:

```bash
specrag search "authentication flow"
specrag search -hy "Figure 4.1"
specrag search -pic "state machine"
specrag msearch "pairing" "authentication" "security"
```

Use `-hy` for exact figure/table names. Use `-pic` when the answer likely lives
in a rendered page, diagram or table.

## Enrichment workflow

After Cline verifies a result, it can improve future retrieval:

```bash
specrag addtag <chunk_id> "authentication flow"
specrag addknowledge <chunk_id> "This rendered page shows the authentication state machine..."
```

Tags are short retrieval labels. Knowledge is a longer explanation or
correction. Both operations call the remote embedding service and replace one
item in FAISS.

## Agent guidelines

- Prefer search before manually browsing long PDFs.
- Rephrase broad questions into two or three targeted searches.
- Inspect `image_path` files before describing diagrams.
- Do not add tags or knowledge unless the result has been verified.
- Keep user-added tags specific and reusable.
- Use `--no-save` for throwaway searches if saved result JSON is not needed.

## Runtime boundary

Cline talks to the RAG CLI/API. The RAG service talks to the embedding service.
Cline should not import model code or run local embedding libraries.

Related docs:

- [Searching](../guides/searching.md)
- [Tagging](../guides/tagging.md)
- [Knowledge](../guides/knowledge.md)
