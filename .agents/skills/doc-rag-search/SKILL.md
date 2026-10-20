---
name: doc-rag-search
description: Search indexed documentation and specifications through the SpecRAG REST API, navigate large specs by clause, table, figure and cross-reference, and look up exact cells in indexed spreadsheets (e.g. channel plans by country and channel). Use when the user asks about content that may be in the indexed documents (specs, requirements, design docs, Excel/CSV tables), asks about a clause/section number, or asks what documents are available.
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
        "page": 953,
        "clause": "9.4.2.17",
        "clause_title": "Channel Switch Announcement element"
      },
      "chunk_id": "/app/data/documents/spec.pdf_12"
    }
  ],
  "latency_ms": 25.6
}
```

- `document` is the full chunk text; quote from it.
- `metadata.file_name` / `source_file` identify the document to cite.
- PDF text chunks carry `page`, and `clause` / `clause_title` when the PDF has
  numbered bookmarks. Use `clause` as the entry point into the structure graph
  below. PDF image results carry `page_number`.
- `similarity` is cosine similarity for a single semantic `query`
  (about 0.5-0.8 for relevant matches). For `queries` or `hybrid` it is a
  fusion score (about 0.01-0.05); compare it only within one response.
- An empty `results` list means nothing matched closely enough. Rephrase with
  more specific or alternative terms, or try `hybrid`.

## Navigate a specification (structure graph)

Large specs (e.g. IEEE 802.11) are indexed with their clause tree and
cross-references ("defined in 9.4.2.1", "see Annex C", "Table 9-277"). Search
finds the entry point; the graph gives the whole clause, what it depends on and
what uses it. Keys are clause numbers (`9.4.2.1`), annexes (`Annex C`, `C.3`),
tables and figures (`Table 9-277`, `Figure 9-963`). Use `--data-urlencode` so
keys with spaces work.

**Clause with its text, parent, children and references:**
```bash
curl -s -G "$BASE/api/v1/graph/node" --data-urlencode "key=9.4.2.17" -d text=true
```

Returns a list, one entry per indexed document that has the key:

```json
[
  {
    "source": "/app/data/documents/80211-2024.pdf",
    "key": "9.4.2.17",
    "kind": "clause",
    "title": "Channel Switch Announcement element",
    "page": 953,
    "parent": {"key": "9.4.2", "title": "Elements"},
    "children": [],
    "chunk_ids": ["/app/data/documents/80211-2024.pdf_6120", "..."],
    "references": [{"key": "11.8.8", "kind": "clause", "title": "...", "mentions": 2}],
    "referenced_by": [{"key": "11.8.8.4.3", "kind": "clause", "title": "...", "mentions": 1}],
    "text": "9.4.2.17 Channel Switch Announcement element ...",
    "text_truncated": false
  }
]
```

- `text` is the clause's own text with chunk overlap removed (max 20000
  chars; `text_truncated` says if it was cut). Subclause text is not included;
  open the `children` you need.
- Omit `text=true` when you only need the structure.
- Add `-d source=80211-2024` to restrict to documents whose path contains that
  text when several versions of a standard are indexed.

**Follow references:**
```bash
curl -s -G "$BASE/api/v1/graph/walk" --data-urlencode "key=9.4.2.17"                  # what it references
curl -s -G "$BASE/api/v1/graph/walk" --data-urlencode "key=9.4.2.17" -d direction=in  # what references it
```

Returns `[{"source": "...", "key": "9.4.2.17", "direction": "in", "nodes": [{"key", "depth", "kind", "title", "page"}]}]`.
`depth` is 1-5 (default 1). Keep it at 1 or 2: hub clauses such as `9.4.2.1`
(the element ID table) are referenced by hundreds of clauses and make deeper
walks noisy.

**Find by title or MIB attribute:**
```bash
curl -s -G "$BASE/api/v1/graph/find" --data-urlencode "q=channel switch"
curl -s -G "$BASE/api/v1/graph/find" --data-urlencode "q=dot11RSNAActivated"
```

Returns `{"nodes": [{"source", "key", "kind", "title", "page"}], "terms": [{"term", "source", "chunks", "sample_chunk_id"}]}`.
Title matching is a case-insensitive substring match, so use a distinctive
phrase from the heading (e.g. "Channel Switch Announcement element").

## Spreadsheets (Excel .xlsx, CSV)

Each table row is indexed as one self-describing chunk: the row label (e.g.
country name and codes) followed by every value with its full header path.
Neighbouring columns with the same value are merged, e.g.

```text
Samsung_WLAN_Channel_Plan_for_Mobile_ver.2.9.1.xlsx › 5GHz
#: 10 | 국가 이름(Country) 1): 그리스 / Greece | column D: 300 | Country Code (alpha-3): GRC | Country Code (alpha-2): GR
5GHz CHANNEL PLAN › U-NII-2C › 5500–5700 › 100, 104, 108, 112, 116, 120, 124, 128, 132, 136, 140: Yes
5GHz CHANNEL PLAN › U-NII-2C › 5720 › 144: No
```

Search results for these chunks carry `metadata.sheet`, `table`, `row` (the
spreadsheet row number) and `row_label`. Search finds the right sheet and row.
**For the actual value, use the exact lookup below** rather than reading
numbers out of search text; numbers inside a merged run (such as channel 120
above) are hard for search to rank.

**Exact lookup:**
```bash
curl -s -G "$BASE/api/v1/tables/lookup" --data-urlencode "row=GR" --data-urlencode "column=144" -d sheet=5GHz
```

```json
{
  "matches": [
    {"source": ".../Samsung_WLAN_Channel_Plan_for_Mobile_ver.2.9.1.xlsx", "sheet": "5GHz", "table_no": 1, "row": 14,
     "label": "#: 10 | 국가 이름(Country) 1): 그리스 / Greece | ...", "column": "5GHz CHANNEL PLAN › U-NII-2C › 5720 › 144", "value": "No"}
  ],
  "row_match": "exact",
  "column_match": "exact",
  "truncated": false
}
```

| Parameter | Matching |
|-----------|----------|
| `row` | A value in the row, e.g. `GR`, `GBR`, `Greece`. Exact (case-insensitive) on any cell first; if nothing matches, a substring of the row-label cells (`row_match: "contains"`). |
| `column` | One header level, e.g. `144`, `5720`, `U-NII-2C`, `Country Code (alpha-2)`. Exact level first, then a substring of the header path. |
| `sheet` | Substring of the sheet name, e.g. `5GHz`. Note `5GHz` also matches `5GHz UNII-4 (NEW)`. |
| `source` | Substring of the file path. |
| `limit` | 1-500, default 200. `truncated: true` means more cells matched. |

Give `row`, `column` or both (400 otherwise). Omit `column` to get the whole
row; omit `row` to get a whole column.

- `row_match: "contains"` can return several rows (e.g. `Korea` matches the
  Republic of Korea and the DPRK). Check `label` and pick the right row, or
  retry with a code such as `KR`.
- A workbook may contain change-log sheets (e.g. `v1.5`, `v2.7`) that repeat
  older rows. Prefer the main sheet (e.g. `5GHz`) for current values, and use
  change-log sheets only to explain history.
- Values are returned as written in the sheet (`Yes`, `Yes indoor only`,
  `Yes (VLP, LPI)`, `No`); quote them, and cite sheet and row, e.g.
  `(Channel_Plan v2.9.1, sheet 5GHz, row 14)`.

**Discover sheets and column names:**
```bash
curl -s "$BASE/api/v1/tables"     # [{"source", "sheet", "table_no", "rows", "label_columns": [...], "value_columns": [...]}]
```

Use this when you do not know a sheet's header paths or which file holds a table.

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
4. For specs, when a result has `metadata.clause` (or the user names a clause,
   table or figure), open it with `graph/node?text=true` instead of stitching
   chunks together. Follow `references` for definitions it depends on and
   `walk?direction=in` for procedures that use it. If you know the heading but
   not the number, use `graph/find`. Cite clause and page, e.g.
   `(802.11-2024, 9.4.2.17, p. 953)`.
5. For spreadsheet questions (a value for a given row and column, such as a
   country and a channel), call `tables/lookup` directly when you can name the
   row and column; otherwise search first, take `metadata.sheet` and
   `row_label` from the hit, then look up the exact cell.
6. If results are weak, say what was searched and that the documents may not
   cover it, instead of filling gaps from general knowledge.

## Errors

| Status | Meaning |
|--------|---------|
| 400 | `tables/lookup` without `row` or `column`. |
| 404 | `graph/node` or `graph/walk`: the key is not in the structure graph. Check the number, try `graph/find`, or fall back to search (documents without bookmarks have no clause tree). |
| 422 | Invalid body or parameter, e.g. neither `query` nor `queries`, `top_k` or `depth` out of range. |
| 503 | Embedding service unavailable; retry shortly or report it. |
| 500 | Server error; report the `detail` message. |
