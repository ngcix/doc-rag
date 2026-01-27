# 🔍 Search Engine Architecture

## Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SEARCH PIPELINE                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌───────────┐ │
│  │  User Query  │───▶│  Vectorize   │───▶│ FAISS Search │───▶│  Results  │ │
│  │   "query"    │    │   (768-dim)  │    │   (Top-K)    │    │  Ranking  │ │
│  └──────────────┘    └──────────────┘    └──────────────┘    └───────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Search Types

| Type | Description | Best For |
|------|-------------|----------|
| Semantic | Vector similarity | Concept search |
| Hybrid | BM25 + Vector (RRF) | Exact + semantic |
| Multi-query | Multiple queries + RRF | Complex questions |

## Semantic Search Flow

```
Query: "authentication flow"
    │
    ▼
Vectorize → [0.12, -0.34, 0.56, ...] (768 dims)
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FAISS Index (in-memory)                       │
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Doc 1 Vector    │  │ Doc 2 Vector    │  │ Doc 3 Vector    │  │
│  │ [0.11, -0.32..] │  │ [0.45, 0.12...] │  │ [0.13, -0.33..] │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│         │                     │                     │           │
│         ▼                     ▼                     ▼           │
│    dot(Q, D1)            dot(Q, D2)            dot(Q, D3)       │
│    = 0.87                = 0.23                = 0.85           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
Sort by score: [D1: 0.87, D3: 0.85, D2: 0.23, ...]
    │
    ▼
Return top_k results with score >= threshold
```

## FAISS Index

```python
# IndexFlatIP for cosine similarity on normalized vectors
index = faiss.IndexFlatIP(768)

# Normalize vectors
faiss.normalize_L2(vectors)

# Search
distances, indices = index.search(query_vector, top_k)
```

**Why IndexFlatIP?**
- Inner Product on normalized vectors = Cosine Similarity
- Exact search (best for < 100K vectors)
- Simple, no training required

## Hybrid Search (BM25 + Vector)

### BM25 Algorithm

```python
# BM25 Score Formula
score(q, d) = Σ IDF(term) × (tf × (k1 + 1)) / (tf + k1 × (1 - b + b × |d|/avgdl))

# Where:
# - IDF(term) = log((N - df + 0.5) / (df + 0.5) + 1)
# - tf = term frequency in document
# - |d| = document length
# - avgdl = average document length
```

### RRF Fusion

Kết hợp BM25 và Vector results:

```python
RRF_score(d) = Σ (weight / (k + rank(d)))

# k = 60 (smoothing constant)
# weight = 0.5 for each source

# Example:
# Vector: [A:1, B:2, C:3]
# BM25:   [B:1, A:2, D:3]
#
# A: 0.5/(60+1) + 0.5/(60+2) = 0.0163
# B: 0.5/(60+2) + 0.5/(60+1) = 0.0163
# C: 0.5/(60+3) = 0.0079
# D: 0.5/(60+3) = 0.0079
#
# Final: [A, B, C, D]
```

## Multi-Query Search

```
Queries: ["bluetooth reconnection", "link loss", "timeout"]
    │
    ├──────────────────┬──────────────────┐
    ▼                  ▼                  ▼
Search Q1          Search Q2          Search Q3
[A, B, C]          [B, D, A]          [C, A, E]
    │                  │                  │
    └──────────────────┴──────────────────┘
                       │
                       ▼
              RRF Merge: [A, B, C, D, E]
```

## SearchResult Class

```python
class SearchResult:
    rank: int           # Position in results
    document: str       # Content
    similarity: float   # Score (0.0-1.0)
    metadata: dict      # source_file, page_number, etc.
    chunk_id: str       # Unique identifier
```

## Tag Boosting Effect

```
Query: "Figure 4.1"

Before tagging:
  Doc content: "Authentication flow diagram..."
  Embedding: E1
  Similarity: 0.65

After addtag "Figure 4.1":
  Doc content: "...Tags: Figure 4.1, Figure 4.1, ..." (10x)
  Embedding: E2
  Similarity: 0.89 ✓ (higher rank)
```

## Performance

| Operation | Complexity | Notes |
|-----------|------------|-------|
| IndexFlatIP search | O(n × d) | n=vectors, d=768 |
| Normalization | O(d) | Once per query |
| Top-K selection | O(n log k) | FAISS optimized |

### Memory Usage

```
768 dims × 4 bytes × N vectors = 3KB per vector

10,000 vectors  ≈ 30 MB
100,000 vectors ≈ 300 MB
1,000,000 vectors ≈ 3 GB
```

## Configuration

```python
# config/settings.py
class SearchConfig(BaseModel):
    top_k: int = 5
    score_threshold: float = 0.7
    include_metadata: bool = True
```

## Result Saving

Results được lưu vào `process/output/`:

```json
{
  "query_id": "query_20251218_105537",
  "query": "authentication",
  "result_count": 5,
  "results": [
    {
      "rank": 1,
      "document": "...",
      "similarity": 0.8542,
      "metadata": {...},
      "chunk_id": "HID.pdf_p30"
    }
  ]
}
```

## Module Structure

```
src/search/
├── __init__.py     # Export: get_search_engine(), SearchResult
├── engine.py       # SearchEngine class (semantic)
└── bm25.py         # BM25Index, HybridSearchEngine
```
