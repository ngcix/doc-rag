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
  -> inspect JSON results (metadata.clause / metadata.page for PDFs)
  -> follow the structure graph: specrag clause / refs / find
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

## Structure graph workflow

For specifications with numbered clauses, search gives the entry point and the
graph gives the context:

```bash
specrag search -hy "Channel Switch Announcement element"   # result metadata.clause = 9.4.2.17
specrag clause 9.4.2.17 --text                              # full clause text and its references
specrag refs 9.4.2.17 --in                                  # procedures that use the element
specrag find "channel switch"                               # clauses whose title matches
```

- Use `clause --text` instead of stitching search chunks together when the
  answer needs a whole clause.
- Follow `references` for definitions a clause depends on, and `referenced_by`
  (or `refs --in`) for behaviour that uses it.
- Use `find` with a `dot11…` name to locate MIB attributes.
- Cite clause numbers and page numbers from the graph or chunk metadata.

See [Structure graph](../guides/structure-graph.md).

## Spreadsheet workflow

For Excel/CSV tables, search finds the sheet and row; exact lookup reads the
value:

```bash
specrag search -hy "Greece 5GHz channel plan"      # metadata.sheet = 5GHz, row_label = ... GR
specrag lookup --row GR --column 144 --sheet 5GHz  # value: No
```

See [Spreadsheets](../guides/spreadsheets.md).

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
