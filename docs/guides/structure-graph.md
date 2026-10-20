# Structure graph

Large specifications already contain a graph: the clause hierarchy in the PDF
bookmarks, and explicit cross-references such as "defined in 9.4.2.1",
"see Annex C" or "shown in Table 9-277". SpecRAG extracts that graph with rules
during ingestion. No LLM or extra model is involved, so the embedding service is
unchanged.

The graph is a navigation aid for an agent. Search finds a starting chunk; the
graph answers "which clause is this, what does it depend on, and what depends
on it".

## What is extracted

| Node | Source | Example key |
| --- | --- | --- |
| Clause | PDF bookmarks (numbered entries only) | `9.4.2.1`, `C`, `C.3` |
| Table / figure | Caption lines such as `Table 9-277—…` | `Table 9-277`, `Figure 9-963` |

| Link | Meaning |
| --- | --- |
| parent / children | Clause hierarchy from the bookmark numbering. |
| references | Clause X mentions clause, table or figure Y. |
| referenced by | The reverse of references. |
| MIB terms | `dot11…` attribute names and the chunks that mention them. |

Short numbers such as `5.2` are only treated as references after words like
"in", "see" or "and", because they are often values. Unit-suffixed values
(`5.2 GHz`) and clause headings are ignored.

PDF chunks also gain `page`, `clause` and `clause_title` metadata, so every
search result says where it lives in the document.

## Requirements

- Text PDFs with numbered bookmarks give the full graph. PDFs without bookmarks
  still get table/figure captions and MIB terms, but no clause tree or
  references.
- Other formats are indexed as before and have no graph.
- Existing indexes need `specrag reindex -fp -y` to gain the graph, page/clause
  metadata and header/footer removal.

## Commands

```bash
specrag clause 9.4.2.1                 # node, parent, children, chunk ids, references
specrag clause "Table 9-277" --text    # include the merged node text
specrag refs 9.4.2.1                   # what 9.4.2.1 references
specrag refs 9.4.2.1 --in --depth 2    # who references it, two hops back
specrag find "Channel Switch Announcement"
specrag find dot11RSNAActivated
```

Add `--source 80211-2024` to restrict to documents whose path contains that
text when several versions of a standard are indexed.

HTTP equivalents:

```text
GET /api/v1/graph/node?key=9.4.2.1&text=true
GET /api/v1/graph/walk?key=9.4.2.1&direction=in&depth=2
GET /api/v1/graph/find?q=Channel%20Switch
GET /api/v1/graph/stats
```

## Storage

The graph is a SQLite file, `graph.sqlite`, inside the FAISS index directory.
Staged re-indexing builds it in the staging directory and swaps it together with
the index. Deleting or re-uploading a document replaces its graph rows.

## Page furniture

Running headers and footers that repeat on at least half the pages (ignoring
digits, so page numbers match) are removed before chunking. On IEEE 802.11-2024
this removed the title block and the licence footer from every page and reduced
the chunk count from 52,410 to 42,323.
