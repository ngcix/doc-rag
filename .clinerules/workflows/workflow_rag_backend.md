---
description: Search information in RAG database and analyze results
---

# Search Workflow

## 1. Basic Search
```bash
python -m src.main search "your query" --top-k 5
```

## 2. Image-Only Search
```bash
python -m src.main search -pic "diagram or figure name"
```

## 3. Hybrid Search (Exact-Match Priority)
Use when searching for specific figure/table names:
```bash
python -m src.main search -hy "Figure 4.1: Media Payload"
```

## 4. Combined (Best for Finding Specific Diagrams)
```bash
python -m src.main search -pic -hy "Interrupt IN Flow Chart"
```

## 5. Boost Relevant Results
If a result is relevant but ranks low, add a tag to boost it:
```bash
python -m src.main addtag <doc_id> "keyword"
```

## 6. View Results
Results are saved in `process/output/query_*.json`

Key fields:
- `chunk_id`: Document ID (use for addtag)
- `image_path`: Path to extracted image
- `similarity`: Relevance score (higher is better)