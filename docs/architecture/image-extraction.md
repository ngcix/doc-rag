# Image extraction

Image extraction lives in `src/specrag/image_extraction/`.

```text
src/specrag/image_extraction/
├── __init__.py
├── extractor.py
└── image_info.py
```

SpecRAG currently supports full-page extraction for PDF pages that appear to
contain useful visual content.

## Full-page mode

```bash
specrag process -fp
specrag reindex -fp -y
```

The extractor scans each PDF page and renders selected pages to
`data/extracted_images/`.

A page is selected when it contains signals such as:

- large embedded images,
- vector drawings,
- figure/table captions,
- many lines or rectangles that look like a table/diagram.

This avoids rendering every page while preserving context around diagrams and
tables.

## Metadata

Rendered pages are indexed as items with metadata such as:

| Field | Meaning |
| --- | --- |
| `type` | `extracted_image` for rendered PDF pages. |
| `image_path` | Saved image file. |
| `source_file` | Original document. |
| `page_number` | Source page number. |
| `region_type` | `fullpage`. |
| `tags` | Auto-extracted caption/figure/table tags. |
| `original_tags` | Tags produced during extraction. |
| `user_tags` | Tags added later by users/agents. |

## Vectorization text

Image items are embedded using surrounding page text, detected captions and
boosted tags. The bitmap itself is not embedded; it is returned as a path so a
vision-capable agent can inspect it after retrieval.

## Libraries

| Library | Purpose |
| --- | --- |
| PyMuPDF | PDF parsing and page rendering. |
| Pillow | Image format handling. |
