# Processing and re-indexing

Processing extracts text, renders useful PDF pages, embeds all items through the
remote embedding service, and writes them to the vector store.

## Recommended: staged re-index

```bash
specrag reindex -fp -y
```

`reindex` builds a fresh FAISS store in a staging directory and swaps it into the
live location only after the full run succeeds. Use it when:

- ingesting a new corpus,
- changing model revision, pooling, normalization, dimension or variant,
- recovering from incompatible/legacy index metadata.

## Incremental processing

```bash
specrag process -fp
```

`process` writes directly to the configured vector store. It is useful during
local iteration, but `reindex` is safer for production cutover.

## Options

| Option | Shortcut | Description |
| --- | --- | --- |
| `--input PATH` | `-i` | Source document directory. |
| `--fullpage` | `-fp` | Render PDF pages with visual content. Required unless `--no-images` is used. |
| `--format png|jpeg|jpg` | `-fmt` | Rendered image format. |
| `--workers auto|N` | `-w` | Parallel workers for extraction/chunking. |
| `--embedding-batch-size N` | | Client batch size for embedding requests. |
| `--no-charts` | | Skip Mermaid/sequence chart processing. |
| `--no-images` | | Skip PDF image extraction. |
| `--yes` | `-y` | `reindex` only: skip replacement confirmation. |

## Supported source files

| Extension | Handling |
| --- | --- |
| `.pdf` | Text extraction and optional full-page image rendering. |
| `.docx` | Text extraction. |
| `.md`, `.markdown` | Text extraction and sequence-chart handling. |
| `.txt` | Text extraction. |

## Full-page extraction

`-fp` renders only pages that appear visually useful. A page is selected when it
contains signals such as a sufficiently large embedded image, vector drawing,
figure/table caption, or table-like line structure.

Rendered pages are stored in `data/extracted_images/` and indexed as searchable
items with metadata including `image_path`, `source_file`, `page_number`,
`region_type` and extracted tags.

## Output

CLI commands print JSON reports. A typical report includes counts for text
chunks, extracted images, charts, indexed items and elapsed time.

## Model compatibility

FAISS metadata stores the embedding fingerprint:

```text
model_id@revision:variant:pooling:normalization:dimension
```

If this fingerprint no longer matches the configured embedding service,
readiness/search/ingest reject the store. Run `specrag reindex -fp -y` after
changing the model contract.
